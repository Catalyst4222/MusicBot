import contextlib
import logging
import random
import re
import time
from asyncio import gather, create_task, get_running_loop
from collections import deque
from typing import TYPE_CHECKING, Coroutine, Optional, Union

from naff import (ActiveVoiceState, Embed, Guild, GuildText,
                      InteractionContext, Client)
from yt_dlp import YoutubeDL

from .utils import (chunk, short_diff_from_time, short_diff_from_unix,
                    sync_to_thread)

if TYPE_CHECKING:
    from .MusicCog import SoundCog

BASIC_OPTS = {
    "format": "webm[abr>0]/bestaudio/best",
    "prefer_ffmpeg": True,
    "quiet": True,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/75.0.3770.80 Safari/537.36 ",
    "cachedir": False,
    "extract_flat": "in_playlist",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

EXPIRE_REGEX = re.compile(r"expire=(\d*)")

logger = logging.getLogger("Myr.music.backend")


class Song:
    __slots__ = (
        "data",
        "url",
        "base_url",
        "original_url",
        "title",
        "author",
        "duration",
        "channel",
        "playlist",
        "start_time",
    )

    def __init__(self, data: dict, base_url: str):
        self.data: dict = data
        self.url: str = data["url"]
        self.base_url: str = base_url

        self.title: str = data.get("title", self.url)
        self.author: Optional[str] = data.get("uploader")
        self.channel: Optional[str] = data.get("channel_url")
        self.playlist: Optional[str] = data.get("playlist")
        self.original_url: Optional[str] = data.get("original_url")
        self.duration: int = data.get("duration") or 0

        self.start_time: Optional[int] = None

    def __len__(self):
        return self.duration

    def __str__(self):
        return self.title

    def ready(self):
        self.start_time = time.time()

    @property
    def elapsed_time(self) -> Optional[str]:
        if self.start_time is None:
            return None
        return (
            f'{short_diff_from_unix(self.start_time)}/{self.duration_str or "unknown"}'
        )

    @property
    def duration_str(self):
        return short_diff_from_time(self.duration)

    @property
    def embed(self) -> Embed:
        embed = Embed(title=self.title)
        embed.set_thumbnail(url=self.data["thumbnail"])
        embed.set_author(name=self.author, url=self.channel)
        embed.add_field(name="Playlist", value=self.playlist)
        embed.add_field(name="Duration", value=self.elapsed_time)

        if self.original_url:
            embed.url = self.original_url
        return embed

    # muscle memory
    def to_embed(self) -> Embed:
        return self.embed

    @property
    def expired(self) -> bool:
        # Youtube media links have expire=unix_time in the url
        res = re.search(EXPIRE_REGEX, self.url)
        if res is None:
            return False
        return time.time() > int(res[1])


class Queue:
    __slots__ = (
        "bot",
        "scale",
        "bound_channel",
        "ctx",
        "queue",
        "extractor",
        "loop",
        "loopqueue",
        "_volume",
        "silent",
        "sticky",
        "now_playing",
        "guild",
        "running",
        "current_player",
    )

    def __init__(self, ctx: InteractionContext):
        self.bot: Client = ctx.bot
        self.scale: SoundCog = ctx.command.scale
        self.bound_channel: GuildText = ctx.channel
        self.guild: Guild = ctx.guild

        self.queue: deque[Song] = deque()
        self.now_playing: Optional[Song] = None
        self.current_player: Optional[ActiveVoiceState] = None
        self._volume = 100
        self.extractor: "Extractor" = Extractor(self)
        self.running: bool = False
        self.loop: bool = False
        self.loopqueue: bool = False

    @property
    def voice(self) -> Optional[ActiveVoiceState]:
        return self.bot.get_bot_voice_state(self.guild.id)

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, new_volume):
        if self.current_player:
            self.current_player.volume = new_volume
        self._volume = new_volume

    async def add(self, song: Union[Song, str], left: bool = False):
        if isinstance(song, str):
            song = await self.extractor.extract_single_vid(song)

        if left:
            self.queue.appendleft(song)
        else:
            self.queue.append(song)

        return song

    def extend(self, songs: list[Song]):
        self.queue.extend(songs)

    def skip(self, amount=1):
        if self.loopqueue:
            queue = self.queue
            queue.extend = [queue.popleft() for _ in range(amount - 1) if len(queue)]
        else:
            with contextlib.suppress(IndexError):
                [self.queue.popleft() for _ in range(amount - 1)]
        self.voice.stop()

        if not self.queue:
            self.cleanup()

    def shuffle(self):
        random.shuffle(self.queue)

    def _send(self, msg, *args, **kwargs):
        return create_task(self.bound_channel.send(msg, *args, **kwargs))

    def cleanup(self):
        self.queue = None
        # self.guild.voice_client.stop()
        if self.voice:
            self.voice.stop()
            self.voice.disconnect()

        if self in self.scale.queues:
            self.scale.queues.remove(self)

    def start(self):
        if self.running:
            return

        self.running = True
        create_task(self._start())

    async def _start(self):
        logger.info(f"Starting a queue in {self.guild.name}")

        while self.queue:
            self.now_playing = np = self.queue.popleft()
            if np.expired:
                self.now_playing = np = await self.add(np.original_url)

            self.current_player = await YTDLAudio.from_url(
                np.url
            )  # Snek streams it live?

            self.current_player.volume = self.volume
            # pprint(np.data)
            self._send(f"Now Playing: **{np.title}**")

            if self.voice is None:
                self._send(
                    "The bot is not in a vc while trying to play a song, there is a possibility of errors"
                )
                break
            await self.voice.play(self.current_player)

            # todo figure out how to have better refresh stuff
            if self.loop:
                await self.add(np, left=True)
            elif self.loopqueue:
                await self.add(np)

        self._send("Queue emptied")
        self.running = False
        self.queue.clear()
        get_running_loop().call_later(5 * 60, self._leave)

    def _leave(self):
        if not self.running and self.voice:
            create_task(self.voice.disconnect())

    # def prime_song(self):
    #     vc = self.voice
    #     if not self.queue:
    #         return
    #
    #     if vc is not None and not vc.is_playing():
    #         self.now_playing = source = self.queue.popleft()
    #         source.ready()
    #         self.bound_channel.send(f"Now playing {source.title}")
    #
    #         player = YTDLAudio.from_url(source.url)
    #         player.volume = self.volume
    #         vc.play(player, after=self.after)
    #
    # def after(self, error=None):
    #     # raise NotImplementedError
    #     # if error is not None:
    #     #     cog = self.bot.get_cog("Events")
    #     #     self._create_task(cog.error_checker(self.ctx, error))
    #
    #     # looping logic, will not affect next song playing
    #     # it just works, no touchy
    #     if not self.loop:
    #         try:
    #             finished = self.queue.pop(0)
    #         except IndexError:
    #             self._send("An error happened managing the queue")
    #             return self.cleanup()
    #         # self._send(f'Finished playing {finished.title}')
    #         if self.loopqueue:
    #             self.queue.append(finished)
    #
    #     if self.queue:
    #         self.prime_song()
    #
    #     else:
    #         self._send("The queue is empty, disconnecting")
    #         return self.cleanup()
    #     # else:
    #     #     self._create_task(self.bound_channel.send(f'Finished playing {finished}'))

    def __len__(self):
        return len(self.queue)


class Extractor:
    def __init__(self, queue: Queue, **options):
        self.queue: Queue = queue
        self._ytdl = YoutubeDL(BASIC_OPTS | options)

    def _extract(self, link: str, download: bool = False) -> dict:
        return self._ytdl.extract_info(link, download=download)

    @sync_to_thread
    def extract_single_vid(self, url: str) -> Song:
        data = self._extract(url)
        if "url" not in data:
            raise ExtractionError("Invalid url")
        return Song(data, base_url=url)

    async def play_single_song(self, url):
        song: Song = await self.extract_single_vid(url)
        await self.queue.add(song)

        # self.queue.prime_song()

        # if not self.queue.voice.is_playing():
        #     await self.queue._send(f"Playing in {self.queue.voice.channel.mention}.")
        # else:
        #     await self.queue._send("File added to queue")

    async def play_playlist(self, url: str):
        # todo figure out how to make neater, possibly semaphore?
        # if 'youtube' not in url:
        #     raise ExtractionError('Only YouTube links support playlists')
        info = self._extract(url)

        # urls = info["entries"]

        coros: list[Coroutine[None, None, Song]] = [
            self.extract_single_vid(item["url"]) for item in iter(info["entries"])
        ]

        msg = await self.queue.bound_channel.send("Processing playlist")

        first = await coros.pop()
        await self.queue.add(first)
        self.queue.start()

        for group in chunk(coros, size=25):
            songs = await gather(*group, return_exceptions=True)
            for item in songs:
                if isinstance(item, Song):
                    await self.queue.add(item)
                else:

                    await msg.channel.send(
                        f"Exception Caught: `{item.__class__.__name__}: {item.msg}`"
                    )

        await msg.reply("Playlist added!")

    async def search_song(self, query: str):
        assert query.startswith("ytsearch:")
        info = self._extract(query)

        song = await self.extract_single_vid(info["entries"][0]["url"])
        song.original_url = info["entries"][0]["url"]

        if len(info["entries"]) > 1:
            # noinspection PyProtectedMember
            await self.queue._send("Something weird happened, DM `Catalyst4#4222`")

        await self.queue.add(song)
        self.queue.start()


class ExtractionError(Exception):
    pass

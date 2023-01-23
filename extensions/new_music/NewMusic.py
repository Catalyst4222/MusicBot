import asyncio

from naff import (ChannelTypes, Client, Extension, GuildVoice,
                  InteractionContext, OptionTypes, slash_command, slash_option)
from naff_audio import YTAudio

from .tools import MusicQueue


class MusicCog(Extension):
    def __init__(self, bot: Client):
        self.bot: Client = bot
        self.queues: dict[int, MusicQueue] = {}

    def get_queue(self, ctx: InteractionContext) -> MusicQueue:
        if queue := self.queues.get(ctx.guild_id):
            return queue

        queue = MusicQueue(ctx.voice_state)
        queue.start()
        self.queues[ctx.guild_id] = queue
        return queue

    @slash_command("join")
    @slash_option(
        "channel",
        "The channel to join",
        OptionTypes.CHANNEL,
        channel_types=[ChannelTypes.GUILD_VOICE],
    )
    async def join(self, ctx: InteractionContext, channel: GuildVoice = None):
        if channel is not None:
            await channel.connect()
        elif ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            return await ctx.send(
                "You must select a channel or be in one", ephemeral=True
            )

        await ctx.send(f"Connected to **{ctx.guild.me.voice.channel.name}**")

    @slash_command("play", description="Play a song!")
    @slash_option("song", "The song to play", 3, True)
    async def play(self, ctx: InteractionContext, song: str):
        await ctx.defer()
        print(song)

        if not ctx.voice_state:
            if not ctx.author.voice:
                return await ctx.send("You must be in a voice channel!")
            await ctx.author.voice.channel.connect()

        queue = self.get_queue(ctx)
        audio = await YTAudio.from_url(song, stream=True)
        # await asyncio.to_thread(audio._create_process)
        audio.pre_buffer()
        # await asyncio.sleep(3)
        # await ctx.voice_state.play(audio)
        queue.put(audio)

        await ctx.send(f"**{audio.entry['title']}** was added to the queue!")

    # @slash_command("now")
    async def now(self, *args):
        ...

    # @now.subcommand("playing", "Get the song that's currently playing")
    async def now_playing(self, ctx: InteractionContext):
        queue = self.get_queue(ctx)
        if queue.now_playing is None:
            return await ctx.send("No song is currently playing")

        # todo show information

    @slash_command("skip", description="Skip the current song")
    async def skip(self, ctx: InteractionContext):
        queue = self.get_queue(ctx)
        await queue.skip()
        await ctx.send("Skipped!")

    @slash_command("queue", description="manage queue stuff")
    async def queue_base(self, ctx, *_, **__):
        ...

    # @queue_base.subcommand(
    #     "show", sub_cmd_description="Show current songs in the queue"
    # )
    async def queue_show(self, ctx):
        queue = self.get_queue(ctx)

        msg = [queue.now_playing.title]
        msg.extend(song.title for song in queue.queue)
        await ctx.send("\n".join(msg))

    @queue_base.subcommand("clear", sub_cmd_description="Clear the queue")
    async def queue_clear(self, ctx):
        queue = self.get_queue(ctx)
        queue.clear()
        await ctx.send("Queue cleared!")



def setup(bot: Client):  # sourcery skip: instance-method-first-arg-name
    MusicCog(bot)

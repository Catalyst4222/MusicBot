import asyncio
from collections import deque

from naff_audio import NaffQueue, YTAudio


class MusicQueue(NaffQueue):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.now_playing: YTAudio | None = None

    # Don't you just love mangling?
    async def __playback_queue(self) -> None:
        """The queue task itself. While the vc is connected, it will play through the enqueued audio"""
        while self.voice_state.connected:
            if self.voice_state.playing:
                await self.voice_state.wait_for_stopped()
            audio: YTAudio
            # noinspection PyTypeChecker
            self.now_playing = audio = await self.pop()

            await self.voice_state.channel.send(
                f"Now playing: **{getattr(audio, 'entry', {}).get('title') or 'UNKNOWN'}**"
            )

            await self.voice_state.play(audio)
            self.now_playing = None

    async def __call__(self) -> None:
        # needed for overrides
        await self.__playback_queue()

    async def skip(self):
        """Skip the current song"""
        await self.voice_state.stop()

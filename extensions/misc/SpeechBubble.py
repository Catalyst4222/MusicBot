import asyncio
from io import BytesIO
from pathlib import Path

from PIL import Image
from naff import CommandTypes, Extension, File, Member, User, context_menu, slash_command
import naff


class SpeechBubble(Extension):

    async def make_speech_bubble(self, data: bytes) -> BytesIO:
        return await asyncio.to_thread(self._make_speech_bubble, data)

    def _make_speech_bubble(self, data: bytes) -> BytesIO:
        # should be ran in a separate thread
        image: Image.Image = Image.open(BytesIO(data))
        bubble: Image.Image = Image.open(Path(__file__).parent / "speech_bubble.png")

        bubble_scale = bubble.height / bubble.width
        bubble = bubble.resize((image.width, int(image.width*bubble_scale)))

        final: Image.Image = Image.new("RGBA", (image.width, image.height + bubble.height))
        final.paste(bubble, (0, 0))
        final.paste(image, (0, bubble.height))

        stream = BytesIO()
        final.save(stream, format="GIF")
        stream.seek(0)

        return stream



    @context_menu("Speech Bubble", CommandTypes.USER, scopes=[817958268097789972])
    async def user_speech_bubble(self, ctx: naff.InteractionContext):
        await ctx.defer()

        target: User | Member = ctx.target
        avatar = await target.display_avatar.fetch(extension=".png", size=4096)
        res = await self.make_speech_bubble(avatar)

        await ctx.send(file=File(res, file_name="bubble.gif"))










def setup(bot):
    return SpeechBubble(bot)
    # pass
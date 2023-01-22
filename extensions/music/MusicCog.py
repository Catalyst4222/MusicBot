import logging

from naff import (
    InteractionContext,
    OptionTypes,
    Extension,
    Client,
    slash_command,
    slash_option,
    GuildVoice,
)

from .classes import Queue

logger = logging.getLogger("Myr.music")


class SoundCog(Extension):
    def __init__(self, bot):
        self.bot: Client = bot
        self.queues: list[Queue] = []

        logger.info("Music cog loaded!")

    def get_queue(self, ctx: InteractionContext) -> Queue:
        for queue in self.queues:
            if ctx.guild == queue.guild:
                return queue

        queue = Queue(ctx)
        self.queues.append(queue)
        return queue

    @slash_command(
        name="join",
        options=[
            {
                "name": "channel",
                "description": "The channel to join",
                "type": 7,  # Channel type
                "required": False,
                "choices": [],
                "channel_types": [2],  # Voice channel
            }
        ],
        scopes=[817958268097789972],
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

    @slash_command("play", "Play a song!")
    @slash_option("song", "The song to play", 3, True)
    async def play(self, ctx: InteractionContext, song: str):
        print(song)
        if not ctx.voice_state:
            if not ctx.author.voice:
                return await ctx.send("You must be in a voice channel!")
            await ctx.author.voice.channel.connect()

        queue = self.get_queue(ctx)
        await queue.add(song)
        await ctx.send("Added song")
        queue.start()

    @slash_command("loop", "Loop the song")
    @slash_option("loop", "If the song should loop", opt_type=OptionTypes.BOOLEAN)
    async def loop_(self, ctx: InteractionContext, loop: bool = None):
        if not ctx.voice_state:
            return await ctx.send("The bot must be in a voice channel!", ephemeral=True)

        queue = self.get_queue(ctx)
        queue.loop = loop if loop is not None else not queue.loop
        await ctx.send(f"Set song loop to {queue.loop}")

    @slash_command("loopqueue", "Loop the queue")
    @slash_option("loop", "If the queue should loop", opt_type=OptionTypes.BOOLEAN)
    async def loop_queue(self, ctx: InteractionContext, loopqueue: bool = None):
        if not ctx.voice_state:
            return await ctx.send("The bot must be in a voice channel!", ephemeral=True)

        queue = self.get_queue(ctx)
        queue.loopqueue = loopqueue if loopqueue is not None else not queue.loopqueue
        await ctx.send(f"Set queue loop to {queue.loopqueue}")

    @slash_command("disconnect", "Disconnect the bot from the vc")
    async def disconnect(self, ctx: InteractionContext):
        if not ctx.voice_state:
            return await ctx.send("The bot is not in a voice channel!", ephemeral=True)
        await ctx.voice_state.disconnect()
        await ctx.send("Disconnected!")

    @slash_command("queue", description="manage queue stuff")
    async def queue_base(self, ctx, *_, **__):
        ...

    @queue_base.subcommand(
        "show", sub_cmd_description="Show current songs in the queue"
    )
    async def queue_show(self, ctx):
        queue = self.get_queue(ctx)

        msg = [queue.now_playing.title]
        msg.extend(song.title for song in queue.queue)
        await ctx.send("\n".join(msg))

    @queue_base.subcommand("clear", sub_cmd_description="Clear the queue")
    async def queue_clear(self, ctx):
        await ctx.send("NotImplemented")


def setup(bot: Client):
    SoundCog(bot)

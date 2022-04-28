import asyncio
import time

import aiosqlite
from dis_snek import (InteractionContext, OptionTypes, Scale, Snake, listen,
                      slash_command, slash_option)


class RemindersCog(Scale):
    def __init__(self, bot: Snake):
        self.bot: Snake = bot
        self.db: aiosqlite.Connection = ...
        self.tasks: dict[int, asyncio.Task] = {}

    @listen()
    async def on_startup(self):
        self.db = await aiosqlite.connect("reminders.db")

        await self.db.execute(
            """CREATE TABLE IF NOT EXISTS reminders (
             id INTEGER PRIMARY KEY,
             user_id INTEGER,
             channel_id INTEGER,
             reminder TEXT,
             time REAL
        )"""
        )

    async def shed(self) -> None:
        super(RemindersCog, self).shed()
        await self.db.close()

    @slash_command(
        name="remindme",
        description="Reminds you of something",
        scopes=[817958268097789972],
    )
    @slash_option(
        name="content",
        description="The content of the reminder",
        opt_type=OptionTypes.STRING,
        required=True,
    )
    @slash_option(
        name="days",
        description="Number of days to wait",
        opt_type=OptionTypes.INTEGER
    )
    @slash_option(
        name="hours",
        description="Number of hours to wait",
        opt_type=OptionTypes.INTEGER,
    )
    @slash_option(
        name="minutes",
        description="Number of minutes to wait",
        opt_type=OptionTypes.INTEGER,
    )
    @slash_option(
        name="seconds",
        description="Number of seconds to wait",
        opt_type=OptionTypes.INTEGER,
    )
    async def remindme(
        self, ctx: InteractionContext, content, days=0, hours=0, minutes=0, seconds=0
    ):  # sourcery skip: avoid-builtin-shadow
        print('a')
        hours += days * 24
        minutes += hours * 60
        seconds += minutes * 60

        if not seconds:
            return await ctx.send("Please enter a valid time.")

        async with self.db.execute("SELECT MAX(id) FROM reminders") as cursor:
            row = await cursor.fetchone()
            # noinspection PyShadowingBuiltins
            id = 0 if row[0] is None else row[0] + 1

        cursor = await self.db.execute(
            "INSERT INTO reminders VALUES (?, ?, ?, ?, ?)",
            (id, ctx.author.id, ctx.channel.id, content, time.time() + seconds)
        )
        await cursor.close()

        await ctx.send(f"You will be reminded <t:{int(time.time()) + seconds}:R>")

        self.tasks[int(time.time()) + seconds] = asyncio.create_task(
            self.send_remind(ctx, int(time.time()) + seconds, content)
        )


    async def send_remind(self, ctx: InteractionContext, wait_until: int, content: str):
        await asyncio.sleep(wait_until - time.time())
        await ctx.author.send(f"Reminder: {content}")
        del self.tasks[wait_until]




# some string copilot made:
r"^remind me to (?P<reminder>.*) in (?P<time>\d+) (?P<unit>seconds|minutes|hours|days|weeks|months|years)$"


# database schema:
# CREATE TABLE reminders(
#     id INTEGER PRIMARY KEY,  # Will be based off time and current id amount
#     user_id INTEGER,  # The user's id
#     channel_id INTEGER,  # The channel the reminder was set in
#     reminder TEXT,  # The reminder itself
#     time REAL,  # When the reminder should be sent, in unix time
# );


def setup(bot: Snake):  # sourcery skip: instance-method-first-arg-name
    RemindersCog(bot)


# show collumn names in the database:

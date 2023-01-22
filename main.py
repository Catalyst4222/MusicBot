import asyncio
from os import getenv

from dotenv import load_dotenv
from loguru import logger
from naff import Client, listen

bot = Client()


@listen()
async def on_ready():
    logger.info("Ready")


bot.load_extension("extensions.new_music.NewMusic")
# bot.load_extension("reminders.RemindersCog")
# do a reminder thing sometime?
# and maybe a welcome message db

load_dotenv()
bot.start(getenv("TOKEN"))

# cleaning up

# noinspection PyUnresolvedReferences
# db = bot.get_scale("RemindersCog").db
# loop = asyncio.get_event_loop()
# loop.run_until_complete(db.close())

for scale in bot.ext.values():
    scale.shed()

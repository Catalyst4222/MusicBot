from os import getenv

from dis_snek import Snake, listen
from dotenv import load_dotenv

bot = Snake()


@listen()
async def on_ready():
    print("Ready!")


bot.load_extension("music.MusicCog")
bot.load_extension("reminders.RemindersCog")
# do a reminder thing sometime?
# and maybe a welcome message db
load_dotenv()
bot.start(getenv("TOKEN"))

from logging import getLogger
import os
from os.path import join, dirname

import coloredlogs
from dotenv import load_dotenv
from slack_bolt import App

import for_paticipants


load_dotenv(join(dirname(__file__), '../.env'))

logger = getLogger(__name__)
logger.setLevel("INFO")
coloredlogs.install(level="INFO", logger=logger)

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    logger=logger,
)

for_paticipants.register(app)
app.start(port=int(os.environ.get("PORT", 3000)))

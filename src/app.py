import json
from logging import getLogger
import os
from os.path import join, dirname

import coloredlogs
from dotenv import load_dotenv
from slack_bolt import App



def read_json(path, logger):
    abs_path = join(dirname(__file__), path)
    with open(abs_path) as f:
        out = json.load(f)
    return out


load_dotenv(join(dirname(__file__), '../.env'))
logger = getLogger(__name__)
logger.setLevel("DEBUG")
coloredlogs.install(level="DEBUG", logger=logger)
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    logger=logger,
)


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    try:
        client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "callback_id": "home_view",
                "blocks": read_json("blocks/home.json", logger)
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


app.start(port=int(os.environ.get("PORT", 3000)))

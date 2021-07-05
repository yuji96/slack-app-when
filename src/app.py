import json
from logging import getLogger
import os
from os.path import join, dirname

import coloredlogs
from dotenv import load_dotenv
from slack_bolt import App, Ack
from slack_sdk import WebClient


load_dotenv(join(dirname(__file__), '../.env'))
logger = getLogger(__name__)
logger.setLevel("INFO")
coloredlogs.install(level="INFO", logger=logger)
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    logger=logger,
)


def read_json(path):
    abs_path = join(dirname(__file__), path)
    with open(abs_path) as f:
        out = json.load(f)
    return out


@app.shortcut("test")
def open_modal_test(ack: Ack, body: dict, client: WebClient):
    ack()
    client.views_open(trigger_id=body["trigger_id"],
                      view=read_json("blocks/modal.json"))


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    try:
        client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "callback_id": "home_view",
                "blocks": read_json("blocks/home.json")
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))

from slack_bolt import Ack
from slack_sdk import WebClient

from app import app
from blocks import read_json


@app.shortcut("test")
def open_modal_test(ack: Ack, body: dict, client: WebClient):
    ack()
    client.views_open(trigger_id=body["trigger_id"],
                      view=read_json("blocks/modal.json"))

import re

import pandas as pd
from slack_bolt import Ack, App
from slack_sdk import WebClient

from blocks.builder import modal_for_host, modal_for_member
from settings import set_logger

logger = set_logger(__name__)


def register(app: App):
    logger.info("register")

    # 開催者用
    app.shortcut("set_schedules-channel")(show_scheduling_form)
    app.shortcut("set_schedules-im")(show_scheduling_form)

    # 参加者用
    app.action("answer_schedule")(show_answer_modal)


def show_scheduling_form(ack: Ack, body: dict, client: WebClient) -> dict:
    """日程調整用 Modal を表示する．"""
    ack()
    modal = modal_for_host(callback_id=body["callback_id"])
    client.views_open(trigger_id=body["trigger_id"], view=modal)


def show_answer_modal(ack: Ack, body: dict, client: WebClient):
    """回答用 Modal を表示する．"""
    ack()

    date_range = pd.date_range(*re.findall(r"\d{4}-\d{2}-\d{2}", str(body))).date.astype(str)
    start_time, end_time = re.findall(r"\d{2}:\d{2}", str(body))
    host_info = body["actions"][0]["value"]

    client.views_open(trigger_id=body["trigger_id"],
                      view=modal_for_member("answer_schedule",
                                            date_range, start_time, end_time, host_info))

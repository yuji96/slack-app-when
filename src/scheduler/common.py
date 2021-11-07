import re

import pandas as pd
from slack_bolt import Ack, App
from slack_sdk import WebClient

from blocks.builder import modal_for_host, modal_for_member
from settings import set_logger
from visualize import Table
from .slack_parser import AnswerFormData, AnswerFormException

logger = set_logger(__name__)


def register(app: App):
    logger.info("register")

    # 開催者用
    app.shortcut("set_schedules-channel")(show_scheduling_form)
    app.shortcut("set_schedules-im")(show_scheduling_form)

    # 参加者用
    app.action("answer_schedule")(show_answer_modal)
    app.view("answer_schedule")(handle_answer_modal)


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


def handle_answer_modal(ack: Ack, body: dict, client: WebClient, view: dict):
    """回答用 Modal の提出を確認する．"""
    try:
        answer = AnswerFormData(view)
        ack()
    except AnswerFormException as e:
        ack(response_action="errors", errors=e.args[0])
        return

    header, *_ = filter(lambda b: b["type"] == "header", view["blocks"])
    host_channel, host_message_ts = header["block_id"].split("-")

    parent_message, *replies = client.conversations_replies(
        channel=host_channel, ts=host_message_ts)["messages"]
    user_display_name = client.users_info(
        user=body["user"]["id"])["user"]["profile"]["display_name"]
    team_id = parent_message["team"]
    bot_user_id = parent_message["user"]

    if not replies:
        table = Table(answer=answer, name=user_display_name, client=client)
    else:
        bot_msg, *_ = [msg for msg in replies if msg["user"] == bot_user_id]
        old_file = bot_msg["files"][0]
        table = Table(answer=answer, name=user_display_name, client=client,
                      file_url=f"https://files.slack.com/files-pri/{team_id}-{old_file['title']}/download/table.pkl")  # noqa

        client.files_delete(file=old_file["id"])
        client.files_delete(file=old_file["title"])

    # HACK: 下の２行は一緒にしてもいいのでは？
    new_pkl_id = table.upload(bot_user_id)
    client.files_upload(content=table.visualize(), filetype="png", title=new_pkl_id,
                        channels=host_channel, thread_ts=host_message_ts)

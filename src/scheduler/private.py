import re

import pandas as pd
from slack_bolt import Ack, App
from slack_sdk import WebClient

from blocks.base import Header
from blocks.builder import message_from_host, modal_for_host, modal_for_member
from settings import set_logger
from .slack_parser import SchedulerCreationFormData
from visualize import Table

logger = set_logger(__name__)


def register(app: App):
    logger.info("register")

    # 開催者用
    app.shortcut("set_schedules-im")(show_scheduling_form)
    app.view("set_schedules-im")(handle_scheduling_form)

    # メッセージのクリック時
    app.action("answer_schedule")(show_answer_modal)
    app.action("not_answer")(send_no_answer)

    # 提出時
    app.view("answer_schedule")(handle_answer_modal)


def show_scheduling_form(ack: Ack, body: dict, client: WebClient) -> dict:
    """日程調整用 Modal を表示する．"""
    ack()
    modal = modal_for_host(callback_id=body["callback_id"])
    client.views_open(trigger_id=body["trigger_id"], view=modal)


def handle_scheduling_form(ack: Ack, body: dict, client: WebClient, view: dict):
    """ホストとメンバーにメッセージを送信する．"""
    data = SchedulerCreationFormData(body, view)

    # TODO: 日時の検証はここで`ack(response_action="errors", errors={...}})` で行う．
    ack()

    header, *sections, actions = message_from_host(**data)

    # 主催者 に作成した調整を送信する
    # HACK: 主催者も参加者のときは2回送信しない（てか、だいたい参加しそう）
    response = client.chat_postMessage(channel=data["host_id"],
                                       text="日程調整を作成しました",
                                       blocks=[Header("時間調整の詳細"), *sections],
                                       as_user=True)

    # 主催者と主催メッセージの情報を追加する
    for button in actions["elements"]:
        button["value"] = f"{response['channel']}-{response['ts']}"

    # 選択したユーザ・チャンネル にメッセージを送信する
    # TODO: チャンネルの場合はbotを招待する
    for channel in data.members:
        client.chat_postMessage(channel=channel,
                                text="日程調整に回答してください",
                                blocks=[header, *sections, actions],
                                as_user=True)


def show_answer_modal(ack: Ack, body: dict, client: WebClient):
    """回答用 Modal を表示する．"""
    ack()

    date_range = pd.date_range(*re.findall(r"\d{4}-\d{2}-\d{2}", str(body))).date.astype(str)
    start_time, end_time = re.findall(r"\d{2}:\d{2}", str(body))
    host_info = body["actions"][0]["value"]

    client.views_open(trigger_id=body["trigger_id"],
                      view=modal_for_member("answer_schedule",
                                            date_range, start_time, end_time, host_info))


def send_no_answer(ack: Ack, body: dict, client: WebClient):
    """参加できない と主催者に送信する．"""

    ack()

    member = body["user"]["id"]
    host_channel, host_message_ts = body["actions"][0]["value"].split('-')

    client.chat_postMessage(text=f"<@{member}> が「不参加」と回答しました。",
                            channel=host_channel,
                            thread_ts=host_message_ts,
                            as_user=True)


def handle_answer_modal(ack: Ack, body: dict, client: WebClient, view: dict):
    """回答用 Modal の提出を確認する．"""

    ack()

    header, *_ = filter(lambda b: b["type"] == "header", view["blocks"])
    host_channel, host_message_ts = header["block_id"].split("-")

    parent_message, *replies = client.conversations_replies(
        channel=host_channel, ts=host_message_ts)["messages"]
    user_display_name = client.users_info(
        user=body["user"]["id"])["user"]["profile"]["display_name"]
    team_id = parent_message["team"]
    bot_user_id = parent_message["user"]

    answer = {k: v["plain_text_input-action"]["value"]
              for k, v in view["state"]["values"].items()}
    _, input_, *_ = view["blocks"]
    start_date, *_, end_date = answer

    if not replies:
        table = Table(answer=answer, name=user_display_name,
                      date_pair=(start_date, end_date),
                      time_pair=input_["element"]["initial_value"].split("-"),
                      client=client)
    else:
        bot_msg, *_ = [msg for msg in replies if msg["user"] == bot_user_id]
        old_file = bot_msg["files"][0]
        table = Table(answer=answer, name=user_display_name,
                      date_pair=(start_date, end_date),
                      time_pair=input_["element"]["initial_value"].split("-"),
                      client=client,
                      file_url=f"https://files.slack.com/files-pri/{team_id}-{old_file['title']}/download/table.pkl")  # noqa

        client.files_delete(file=old_file["id"])
        client.files_delete(file=old_file["title"])

    # TODO: 下の２行は一緒にしてもいいのでは？
    new_pkl_id = table.upload(bot_user_id)
    client.files_upload(content=table.visualize(), filetype="png", title=new_pkl_id,
                        channels=host_channel, thread_ts=host_message_ts)

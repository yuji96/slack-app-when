from slack_bolt import Ack, App
from slack_sdk import WebClient

from blocks.builder import message_from_host
from settings import set_logger
from .slack_parser import SchedulerCreationFormData
from visualize import Table

logger = set_logger(__name__)


def register(app: App):
    logger.info("register")

    # 開催者用
    app.view("set_schedules-channel")(handle_scheduling_form)

    # 参加者用
    app.action("not_answer")(send_no_answer)


def handle_scheduling_form(ack: Ack, body: dict, client: WebClient, view: dict):
    """ホストとメンバーにメッセージを送信する．"""
    data = SchedulerCreationFormData(body)

    # HACK: 日時の検証はここで`ack(response_action="errors", errors={...}})` で行う．
    ack()

    client.conversations_join(channel=data.channel)

    header, *sections, actions = message_from_host(**data)
    response = client.chat_postMessage(channel=data.channel,
                                       text="日程調整に回答してください",
                                       blocks=[header, *sections, actions],
                                       as_user=True)

    # FIXME: ここの channel-ts が公開設定で変わる。
    # 主催者と主催メッセージの情報を追加する
    for button in actions["elements"]:
        button["value"] = f"{response['channel']}-{response['ts']}"

    # 選択したチャンネルにメッセージを送信する
    client.chat_update(channel=response['channel'],
                       ts=response['ts'],
                       text="日程調整に回答してください",
                       blocks=[header, *sections, actions],
                       as_user=True)


def send_no_answer(ack: Ack, body: dict, client: WebClient):
    """参加できない と主催者に送信する．"""

    ack()

    member = body["user"]["id"]
    host_channel, host_message_ts = body["actions"][0]["value"].split('-')

    client.chat_postMessage(text=f"<@{member}> が「不参加」と回答しました。",
                            channel=host_channel,
                            thread_ts=host_message_ts,
                            as_user=True)

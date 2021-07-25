"""スケジュール調整を主催する為の機能"""

from datetime import datetime, timedelta

from slack_bolt import Ack
from slack_sdk import WebClient

from blocks import read_json
from blocks.base import Header
from blocks.builder import message_from_host, modal_for_host
from response import Data
from settings import set_logger


logger = set_logger(__name__)


def register(app):
    logger.info("register")

    # ホームタブを表示
    app.event("app_home_opened")(home_tab)

    # ホームタブからモーダルを発動
    app.action("set_schedules-channel")(open_modal)
    app.action("set_schedules-im")(open_modal)

    # ショートカットからモーダルを発動
    app.shortcut("set_schedules-channel")(open_modal)
    app.shortcut("set_schedules-im")(open_modal)

    # モーダル入力時
    app.action("host_datepicker-action")(update_modal)
    app.action("host_timepicker-action")(update_modal)

    # 作成完了と回答依頼を送信
    app.view("set_schedules-im")(post_message)
    app.view("set_schedules-channel")(post_message)


def home_tab(client: WebClient, event: dict) -> dict:
    """アプリホームビューを編集する．"""
    client.views_publish(user_id=event["user"],
                         view=read_json("./app_tab/home.json"))


def open_modal(ack: Ack, body: dict, client: WebClient, view: dict) -> dict:
    """日程調整用 Modal を表示する．"""

    if "actions" in body:
        # アプリホームビュー から
        callback_id = str(body["actions"][0]["action_id"])
    else:
        # ショートカット から
        callback_id = str(body["callback_id"])

    modal = modal_for_host(callback_id=callback_id)

    ack()
    client.views_open(trigger_id=body["trigger_id"], view=modal)


def update_modal(ack: Ack, body: dict, client: WebClient):
    """日程調整用 Modal の内容を更新する．"""

    view_json = read_json("./modals/set_schedules.json")

    # 更新する内容
    view_json["blocks"] = body["view"]["blocks"]
    view_json["callback_id"] = body["view"]["callback_id"]

    # TODO: 入力した時間と日程が有効かどうか確認する

    ack()

    # モーダルを更新する
    client.views_update(
        view=view_json,
        hash=body["view"]["hash"],
        view_id=body["view"]["id"])


def post_message(ack: Ack, body: dict, client: WebClient, view: dict):
    """ホストとメンバーにメッセージを送信する．"""
    data = Data(body, view)
    ack()
    header, *sections, actions = message_from_host(**data)

    # 主催者 に作成した調整を送信する
    response = client.chat_postMessage(channel=data["host_id"],
                                       text="日程調整を作成しました",
                                       blocks=[Header(text="時間調整の詳細"), *sections],
                                       as_user=True)

    # 主催者と主催メッセージの情報を追加する
    for button in actions["elements"]:
        button["value"] = f"{response['channel']}-{data['host_id']}-{response['ts']}"

    # 選択したユーザ・チャンネル にメッセージを送信する
    for item in data.members:
        client.chat_postMessage(channel=item,
                                text="日程調整に回答してください",
                                blocks=[header, *sections, actions],
                                as_user=True)

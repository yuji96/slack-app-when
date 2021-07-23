"""スケジュール調整を主催する為の機能"""

from datetime import datetime, timedelta

from slack_bolt import Ack
from slack_sdk import WebClient

from blocks import read_json
from blocks.base import Header
from blocks.builder import from_host
from response import Data
from settings import set_logger


logger = set_logger(__name__)


def home_tab(client: WebClient, event: dict) -> dict:
    """アプリホームビューを編集する．"""
    client.views_publish(user_id=event["user"],
                         view=read_json("./app_tab/home.json"))


def open_modal(ack: Ack, body: dict, client: WebClient, view: dict) -> dict:
    """日程調整用 Modal を表示する．"""
    view_json = read_json("./modals/set_schedules.json")

    if "actions" in body:
        # アプリホームビュー から
        target_id = str(body["actions"][0]["action_id"])
    else:
        # ショートカット から
        target_id = str(body["callback_id"])
    view_json["callback_id"] = target_id
    target = target_id.removeprefix("set_schedules-")

    # モーダルのブロック を追加
    view_json["blocks"] = insert_block(target)

    ack()

    # モーダルを開く
    client.views_open(
        trigger_id=body["trigger_id"],
        view=view_json)


def insert_block(target: str) -> list:
    """日程調整用 Modal のブロックを追加する．"""

    insert_blocks = []

    # 日程調整用 Modal ブロックのディレクトリ
    directory = "./set"

    # 日程選択 のブロック
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    date_json = read_json(f"{directory}/set_date.json")

    # 開始日 ->「今日」、終了日 ->「明日」 に設定
    date_json[1]['accessory']['initial_date'] = str(today.date())
    date_json[2]['accessory']['initial_date'] = str(tomorrow.date())

    insert_blocks.extend(date_json)

    # 時間選択 のブロック
    time_json = read_json(f"{directory}/set_time.json")
    insert_blocks.extend(time_json)

    # 回答者選択 のブロック
    target_json = read_json(f"{directory}/set_{target}.json")
    insert_blocks.extend(target_json)

    # チャンネル用の共有設定 のブロック
    if target == "channel":
        display_json = read_json(f"{directory}/set_display.json")
        insert_blocks.extend(display_json)

    return insert_blocks


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
    header, *sections, actions = from_host(**data)

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


def register(app):
    logger.info("register")

    # アプリのタブ イベント
    app.event("app_home_opened")(home_tab)

    # 日程調整の開始
    app.view("set_schedules-im")(post_message)
    app.view("set_schedules-channel")(post_message)

    # アプリのタブ内 モーダル発動 イベント
    app.action("set_schedules-channel")(open_modal)
    app.action("set_schedules-im")(open_modal)

    # ショートカット モーダル発動 イベント
    app.shortcut("set_schedules-channel")(open_modal)
    app.shortcut("set_schedules-im")(open_modal)

    # モーダル入力時
    app.action("host_datepicker-action")(update_modal)
    app.action("host_timepicker-action")(update_modal)


##########################################
# utilities
##########################################


def build_schedule_block(target: str) -> list:
    """日程調整用 Modal のブロックを追加する．"""

    insert_blocks = []

    # 日程調整用 Modal ブロックのディレクトリ
    directory = "./set"

    # 日程選択 のブロック
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    date_json = read_json(f"{directory}/set_date.json")

    # 開始日 ->「今日」、終了日 ->「明日」 に設定
    date_json[1]['accessory']['initial_date'] = str(today.date())
    date_json[2]['accessory']['initial_date'] = str(tomorrow.date())

    insert_blocks.extend(date_json)

    # 時間選択 のブロック
    time_json = read_json(f"{directory}/set_time.json")
    insert_blocks.extend(time_json)

    # 回答者選択 のブロック
    target_json = read_json(f"{directory}/set_{target}.json")
    insert_blocks.extend(target_json)

    # チャンネル用の共有設定 のブロック
    if target == "channel":
        display_json = read_json(f"{directory}/set_display.json")
        insert_blocks.extend(display_json)

    return insert_blocks

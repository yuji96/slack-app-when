from slack_bolt import Ack
from slack_sdk import WebClient

from datetime import datetime, timedelta

from blocks import read_json
from settings import set_logger


logger = set_logger(__name__)


def home_tab(client, event, logger):
    """アプリホームビューを編集する．"""
    blocks = read_json("./statics/home.json")
    client.views_publish(
        user_id=event["user"],
        view={
            "type": "home",
            "callback_id": "home_view",
            "blocks": blocks
        }
    )

def set_target(ack: Ack, body: dict, client: WebClient):

    ack()
    view_json = read_json("./modals/set_target.json")

    client.views_open(trigger_id=body["trigger_id"],
                      view=view_json)

def check_target(ack: Ack, body: dict, client: WebClient, view: dict):

    ack()
    block_id = body["view"]["blocks"][0]["block_id"]
    target_value = view["state"]["values"][block_id]["target-select"]["selected_option"]["value"]

    set_schedule(body["trigger_id"],client,target_value)

def set_schedule(trigger_id, client: WebClient, target):
    """日程調整用 Modal を表示する．"""
    read_file = "./modals/set_schedule-"+target+".json"
    view_json = read_json(read_file)

    # 開始日を「今日」に、終了日を「明日」に設定
    today = datetime.today()
    tomorrow = today + timedelta(1)
    view_json["blocks"][1]['accessory']['initial_date'] = str(today.date())
    view_json["blocks"][2]['accessory']['initial_date'] = str(tomorrow.date())

    if "channel" in target:
        
        # TODO:OPTION追加用のモーダルを作成
        options = [ {
                        'text': {
                            'type': 'plain_text', 
                            'text': item["name"], 
                            'emoji': True
                        }, 
                        'value': item["id"]
                    } for item in client.conversations_list(types=target)['channels']]
        
        view_json["blocks"][6]["element"]["options"] = options

    client.views_open(trigger_id=trigger_id,
                      view=view_json)

def update_schedule(ack: Ack, body: dict, client: WebClient):
    """日程調整用 Modal の内容を更新する．"""
    ack()
    view_json = read_json("./modals/set_schedule.json")
    view_json["blocks"] = body["view"]["blocks"]

    client.views_update(view=view_json,
                        hash=body["view"]["hash"],
                        view_id=body["view"]["id"])

def check_users(ack: Ack, body: dict, client: WebClient, view: dict):
    """日程調整用 Modal の提出を処理する．"""
    ack()
    block_id = body["view"]["blocks"][6]["block_id"]
    users_list = view["state"]["values"][block_id]["multi_users_select-action"]["selected_users"]

    send_message(users_list,client)

def check_channels(ack: Ack, body: dict, client: WebClient, view: dict):

    ack()
    block_id = body["view"]["blocks"][6]["block_id"]
    channel = [list(view["state"]["values"][block_id].values())[0]['selected_option']['value']]

    send_message(channel,client)

def send_message(lists: list, client: WebClient):

    # 選択したユーザ・チャンネルにメッセージを投稿する
    for item in lists:

        client.chat_postMessage(channel=item,
                                text="Please Check the message",
                                blocks=read_json("./statics/hello.json"))

def register(app):
    logger.info("register")

    # TODO: `Calleback ID` の命名規則を統一したい．

    # アプリのタブ　イベント
    app.event("app_home_opened")(home_tab)

    # モーダル発動　イベント
    app.action("schedule-request")(set_target)
    app.shortcut("schedule-request")(set_target)

    # モーダル入力時
    app.action("datepicker-action")(update_schedule)
    app.action("multi_conversations_select-action")(update_schedule)
    app.action("result-option")(update_schedule)

    # モーダル提出時
    app.view("schedule-request")(check_target)
    app.view("set-schedules-private-DM")(check_users)
    app.view("set-schedules-public-channel")(check_channels)

from slack_bolt import Ack
from slack_sdk import WebClient

from datetime import datetime,timedelta

from blocks import read_json
from settings import set_logger


logger = set_logger(__name__)


# TODO: チュートリアルの関数なので将来的に削除する
def home_tab(client, event, logger):
    logger.info("open")
    blocks = read_json("./statics/home.json")
    try:
        client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "callback_id": "home_view",
                "blocks": blocks
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")

# Modalの新規作成時
def set_schedule(ack: Ack, body: dict, client: WebClient):
    ack()
    view_json = read_json("./modals/set_schedule.json")
    today = datetime.today()
    tomorrow = today + timedelta(1)

    #　開始日を「今日」に、終了日を「明日」に設定
    view_json["blocks"][1]['accessory']['initial_date']=str(today.date())
    view_json["blocks"][2]['accessory']['initial_date']=str(tomorrow.date())

    client.views_open(trigger_id=body["trigger_id"],
                      view=view_json)

# Modalの更新時
def update_schedule(ack: Ack, body: dict, client: WebClient):
 
    ack()
    action_block = body["actions"][0]["block_id"]
    insert_value = body["view"]["state"]["values"][action_block]
    view_json = read_json("./modals/set_schedule.json")
    view_json["blocks"] = body["view"]["blocks"]

    client.views_update(view=view_json,
                        hash=body["view"]["hash"],
                        view_id=body["view"]["id"])

# Modalの提出時
def send_message(ack: Ack, body: dict, client: WebClient):

    ack()
    users_list_block = body["view"]["blocks"][7]["block_id"]
    users_list = body["view"]["state"]["values"][users_list_block]['multi_conversations_select-action']['selected_conversations']

    if users_list != []:
        
        # 選択したユーザ・チャンネルにメッセージを投稿する
        for item in users_list:
            client.chat_postMessage(channel=item,
                                    text="This is a test",
                                    blocks=read_json("./statics/hello.json"))

    else:

        # TODO:　モーダルにて選択のValidationを設定する必要がある    

        """
        view_json = read_json("./modals/set_schedule.json")
        view_json["blocks"] = body["view"]["blocks"]
        client.view(view=view_json,
                            hash=body["view"]["hash"],
                            view_id=body["view"]["id"])
        """
        pass

def register(app):
    logger.info("register")

    # アプリのタブ　イベント
    app.event("app_home_opened")(home_tab)

    # モーダル発動　イベント
    app.shortcut("set_schedules")(set_schedule)
    app.action("set-schedules")(set_schedule)

    # モーダル入力時
    app.action("datepicker-action")(update_schedule)
    app.action("multi_conversations_select-action")(update_schedule)
    app.action("result-option")(update_schedule)

    # モーダル提出時
    app.view("set-schedules")(send_message)
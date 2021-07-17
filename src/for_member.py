"""　スケジュール調整に参加する為の機能 """

import dataclasses
import datetime as dt
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from slack_bolt import Ack
from slack_sdk import WebClient

from blocks import read_json
from settings import set_logger, TMP_DIR

# TODO: デバッグ用で開発後には削除する
from pprint import pprint


logger = set_logger(__name__)


def open_modal(ack: Ack, body: dict, client: WebClient):
    """回答用 Modal を表示する．"""

    view_json = read_json("./modals/answer_schedule.json")

    #　モーダルのブロック を追加
    view_json["blocks"], time = insert_block(body)

    ack()

    # モーダルを開く
    client.views_open(
        trigger_id = body["trigger_id"],
        view = view_json)


def insert_block(body: dict) -> list:
    """回答用 Modal のブロックを追加する．"""

    insert_blocks=[]
    values = {}

    # [主催者、日、時間、設定] をメッセージから取得する
    items = [ 'host', 'date', 'time', 'setting' ]
    for item in body["message"]["blocks"] :
        if "block_id" in item and item["block_id"] in items:
            values[ item["block_id"] ] = item["text"]["text"].split("\n")[1]

    # 開催日から終了日の間　の日付を生成する
    dates = values["date"].split(" から ")
    values["date"] = [ str(item.date()) for 
        item in list(pd.date_range(dates[0],dates[1])) ]

    # 時間選択　のブロック
    for item in values["date"]:
        insert_blocks.extend(generate_block(item,values["time"],1))

    # 主催者宛　のブロック
    users_json = generate_description_block(body["actions"][-1]["value"])
    insert_blocks.extend(users_json)

    return insert_blocks, values["time"]


def generate_block(date: str, time: str, num: int) -> list:
    """回答用 Modal のブロックを追加する．"""

    divider_block = {"type": "divider"}

    # Pattern 1
    pattern = [divider_block, generate_date_block(date,time), 
        generate_time_block(date,time,num),generate_options_block(date,"None")]

    # Pattern 2
    pattern = [divider_block,generate_label_block(date,time),
        generate_options_block(date)]

    return pattern


def generate_date_block(date: str, time: str) -> dict:
    """回答用 Modal の日にちのブロックを追加する．"""

    date_block = read_json("./answer/add_date.json")
    date_block["block_id"] = date
    date_block["text"]["text"] = date_block["text"]["text"].replace("date",date).replace("time",time)
    date_block["accessory"]["value"] += f"-{date}"

    return date_block


def generate_time_block(date: str, time: str, num: int)  -> dict:
    """回答用 Modal の時間選択のブロックを追加する．"""

    start_time,end_time =  time.split(" から ")

    time_block = read_json("./answer/add_time.json")
    time_block["block_id"] = time_block["block_id"].replace("date",date).replace("opt",str(num))
    time_block["elements"][0]["initial_time"] = start_time
    time_block["elements"][1]["initial_time"] = end_time

    return time_block


def generate_label_block(date = "", time = ""):

    label_json = read_json("./answer/add_date-text.json")

    label_json["block_id"] = date
    label_json["label"]["text"] = label_json["label"]["text"].replace("date",date).replace("time",time)

    return label_json


def generate_label_element(initial: str):

    label_json = read_json("./answer/add_date-text-initial.json")

    label_json["initial_value"] = initial

    return label_json


def generate_options_block(date: str, value = "default"):

    option_json = read_json("./answer/add_button_options.json")
    option_json["block_id"] = f"{date}-opt"
    if value == "yes":
        option_json["elements"][0]["style"] = "primary"
    elif value == "no":
        option_json["elements"][-1]["style"] = "danger"

    return option_json


def generate_description_block(value: str):

    description_json = [read_json("./answer/add_description.json")]
    description_json[0]["elements"][0]["text"] += f"<@{value.split('-')[1]}>"
    description_json[0]["elements"][1]["alt_text"] = value

    """
    host_json=read_json("./answer/add_host.json")
    host_json["value"] = value

    description_json=read_json("./answer/add_user.json")
    description_json[-1]["element"]["initial_option"]=host_json
    description_json[-1]["element"]["options"].append(host_json)
    """

    return description_json


def update_modal(ack: Ack, body: dict, client: WebClient):
    """回答用 Modal のブロックを更新する．"""

    view_json = read_json("./modals/answer_schedule.json")
    view_json["blocks"] = body["view"]["blocks"]
    target = body["actions"][0]["block_id"]
    action = body["actions"][0]["action_id"]

    """
    # Pattern 1
    # 時間設定のブロック　を追加する
    if action == "member-add_date":
        target_blocks = update_option(body)

    # 入力した時間 に設定する
    else:
        target_blocks = update_time(body)
    """

    # Pattern 2
    if "click_option" in action:

        button_select = action.split('-')[-1]
        date = target.removesuffix("-opt")

        for index,item in enumerate(view_json["blocks"]):
            if item["block_id"] == target:
                
                value = view_json["blocks"][index-1]["element"]
                
                pprint(body)
                if "initial_value" in value:
                    condition = (
                        (value["initial_value"] == "All" and button_select == "no") or
                        (value["initial_value"] == "None" and button_select == "yes") or
                        (value["initial_value"] not in ["All","None"]) )
                else:
                    condition = "initial_value" not in value
                print(condition)
                if condition:

                    update_button_json = generate_options_block(date,button_select)
                    body["view"]["state"]["values"][date]["plain_text_input-action"]["value"] = None

                    if button_select == "yes":
                        value = generate_label_element("All")  
                    else:
                        value = generate_label_element("None")
                    view_json["blocks"][index-1]["element"] = value

                else:
                    
                    
                    print(condition)
                    update_button_json = generate_options_block(date)
                    view_json["blocks"][index-1]["element"] = generate_label_block()["element"]
                
                item["elements"] = update_button_json["elements"]
                
                    

                break
        
        body["view"]["state"]["values"][date]["plain_text_input-action"]["value"] = value

    ack()

    # モーダルを　更新する
    client.views_update(
        view = view_json,
        hash = body["view"]["hash"],
        view_id = body["view"]["id"])


def update_option(body: dict) -> dict:
    """回答用 Modal の時間選択ブロックを追加更新する．"""

    target_date = body["actions"][0]["block_id"]
    temp = body["view"]["blocks"]

    target_blocks = [ item for item in temp 
        if "block_id" in item and target_date in item["block_id"] ]

    option_num = len(target_blocks)
    option_time = str(target_blocks[0]["text"]["text"].split("の")[-1].strip(' *'))

    for i in range(len(temp)):
        if target_date in temp[i]["block_id"] :
                temp.insert(i+2,generate_time_block(target_date,option_time,option_num))
                break

    return temp


def update_time(body: dict) -> dict:
    """回答用 Modal の時間選択ブロックを更新する．"""

    #TODO:　入力した時間が有効か確認する
    #TODO:　重複しているか確認

    return body["view"]["blocks"]


def get_modal_inputs(body: dict, values: dict) -> dict:
    """回答用 Modal の 入力を取得する．"""

    member = body["user"]["id"]
    target = body["view"]["blocks"][-1]["elements"][0]["text"].split(':')[-1]
    secret = body["view"]["blocks"][-1]["elements"][1]["alt_text"]
    dates,date = {}, "date"

    # 入力した日時を取得する
    """
    # Pattern 1
    date_list = sorted(list(values.keys()))
    for item in date_list:

        temp = values[item]
        if date not in item:
            date = item[:-2]
            dates[date] = []

        if temp["member_check-action"]["selected_options"] is None:
            # TODO:終日用に設定する
            sets = []
        else:
            sets = [ temp["member_start-timepicker-action"]["selected_time"], 
                     temp["member_end-timepicker-action"]["selected_time"] ]

        dates[date].append(sets)
    """

    # Pattern 2
    for item in values:
        dates[item] = values[item]["plain_text_input-action"]["value"]

    return {
        "target" : target,
        "secret_value" : secret,
        "available_date" : dates,
        "member" : member
    }


def get_message(value: str, client: WebClient):
    """主催者の スケージュール調整詳細メッセージ を取得する"""

    target_channel, host, post_time = value.split('-')

    # Target message
    message_list = client.conversations_history(
        channel = target_channel,
        oldest = post_time,
        inclusive = True,
        limit=1)["messages"]
    
    if message_list == []:
        return None

    message_info = message_list[0]
    target_message = message_info["ts"]

    result = { "channel" : target_channel }

    # スレッドの確認
    thread_present = False
    if "thread_ts" in message_info:
        thread_present = True

        reply_content = client.conversations_replies(
            channel = target_channel,
            ts = message_info["thread_ts"],
            )["messages"][-1]

        target_message = reply_content["ts"]
        message_content = reply_content["blocks"][0]["text"]["text"]
        
        result["message"] = message_content
    
    result["thread_present"] = thread_present
    result["channel"] = target_channel
    result["ts"] = target_message

    return result


def check_modal(ack: Ack, body: dict, client: WebClient, view: dict):
    """回答用 Modal の提出を確認する．"""

    values = view["state"]["values"]
    inputs = get_modal_inputs(body,values)
    secret_value = inputs["secret_value"]

    ack()
    
    #　メッセージを送信する
    send_answer(inputs,secret_value,client)


def send_answer(inputs: dict, secret_value: str, client: WebClient):
    """回答用 Modal の提出を確認メッセージを送信する．"""

    #　スケジュール調整の詳細メッセージスレッドを取得
    result = get_message(secret_value,client)

    message_json = read_json("./message/from_member-yes.json")
    message_json[0]["text"]["text"] = message_json[0]["text"]["text"].replace("I",f"<@{inputs['member']}>")

    if result["thread_present"]:
        message_json[0]["text"]["text"] += f"\n{result['message']}"
    
    # 主催者にメッセージを送信する
    send_host(
        thread=result["thread_present"],
        target_channel=result["channel"],
        target_message=result["ts"],
        input_block=message_json,
        client=client
    )

    # モーダルの入力を表示する
    print(f"\n\nモーダルの入力")
    pprint({"result" : inputs['available_date']})


def send_not_answer(ack: Ack, body: dict, client: WebClient):
    """参加できない　と主催者に送信する．"""

    member = body["user"]["id"]
    secret_value = body["actions"][0]["value"]
    
    #　スケジュール調整の詳細メッセージスレッドを取得
    result = get_message(secret_value, client)

    message_json = read_json("./message/from_member-no.json")
    message_json[0]["text"]["text"] = message_json[0]["text"]["text"].replace("I",f"<@{member}>")
    
    if result["thread_present"]:
        message_json[0]["text"]["text"] += f"\n{result['message']}"
    
    ack()

    # 主催者にメッセージを送信する
    send_host(
        thread=result["thread_present"],
        target_channel=result["channel"],
        target_message=result["ts"],
        input_block=message_json,
        client=client
    )


def send_host(thread: bool, target_channel: str, target_message: str, input_block: dict, client: WebClient):
    """ 主催者に送る """

    # スレッドの確認
    if thread:
        client.chat_update(
            channel = target_channel,
            text = "メッセージを確認してください",
            blocks = input_block,
            ts = target_message,
            as_user = True)
    else:
        client.chat_postMessage(
            channel = target_channel,
            text = "メッセージを確認してください",
            blocks = input_block,
            thread_ts = target_message,
            as_user = True)


def register(app):
    logger.info("register")
    
    # メッセージのクリック時
    app.action("answer_schedule")(open_modal)
    app.action("not_answer")(send_not_answer)

    # 「追加」ボタンのクリック時
    app.action("member-add_date")(update_modal)

    # 時間の選択時
    #app.action("member_start-timepicker-action")(update_modal)
    #app.action("member_end-timepicker-action")(update_modal)
    #app.action("member_check-action")(update_modal)
    
    app.action("click_option-yes")(update_modal)
    app.action("click_option-no")(update_modal)

    # 提出時
    app.view("answer_schedule")(check_modal)


##########################################
# utilities
##########################################


@dataclasses.dataclass
class Table:
    data: dataclasses.InitVar[dict]
    name: str
    date_pair: tuple[dt.date, dt.date]
    time_pair: tuple[dt.time, dt.time]

    slots: list = dataclasses.field(init=False, default_factory=list)
    df: pd.DataFrame = dataclasses.field(init=False)

    def __post_init__(self, data):
        for date, text in data.items():
            self.slots.extend(self.input_to_datetime(date, text))
        self.df = self.create_time_table()

    @staticmethod
    def input_to_datetime(date: dt.datetime, text: str):
        """ユーザーの入力を日付型に変換する．

        Examples
        --------
        >>> table = Table('9 : 00 -11 : 00, 14:30  ~ 18:00')
        >>> table.slots
        [(datetime.datetime(2021, 5, 11, 9, 0), datetime.datetime(2021, 5, 11, 11, 0)), (datetime.datetime(2021, 5, 11, 14, 30), datetime.datetime(2021, 5, 11, 18, 0))]
        >>> table = Table('13:00-11:00')
        Traceback (most recent call last):
        ...
        ValueError: `13:00-11:00` の入力が正しくありません。

        """
        def to_datetime(date: dt.date, str_time: str) -> dt.datetime:
            format = "%H:%M" if ":" in str_time else "%H%M"
            time = dt.datetime.strptime(str_time, format).time()
            return dt.datetime.combine(date, time)

        # TODO: 半角に変換
        # TODO: `15:00-` に対応する
        text = re.sub(r"\s*([:\-~,])\s*", r"\1", text)
        str_slots = text.split(",")

        for str_start, str_end in map(lambda slot: re.split(r"[\-~]", slot), str_slots):
            start = to_datetime(date, str_start)
            end = to_datetime(date, str_end)
            if end <= start:
                raise ValueError(f"`{str_start}-{str_end}` の入力が正しくありません。")
            yield (start, end)

    def create_time_table(self):
        """空いている時間の表を作成する．"""
        # TODO: 強制的に30分区切りにする処理を追加する．
        start = dt.datetime.combine(self.date_pair[0], self.time_pair[0])
        end = dt.datetime.combine(self.date_pair[1], self.time_pair[1])

        index = pd.date_range(start, end, freq=dt.timedelta(minutes=30))
        single = pd.Series(False, index=index)
        for s, e in self.slots:
            single[s:e] = True

        single.set_axis([index.date, index.time], axis="index", inplace=True)
        table = single.unstack().loc[:, start.time():end.time()]
        return table.astype(bool)

    def visualize(self):
        # TODO: レイアウトの調整
        w = len(self.df.columns)
        figsize = np.array(self.df.T.shape) * 10.5 / w
        fig, ax = plt.subplots(figsize=figsize)
        sns.heatmap(self.df, cbar=False, square=True,
                    cmap="Blues", alpha=0.7,
                    linecolor="grey", linewidths=0.2)
        plt.savefig(f"{TMP_DIR}/table.png")


if __name__ == "__main__":
    data = {dt.date(2021, 7, 10): '9 : 00 -11 : 00, 14:30  ~ 18:00'}
    name = "yuji"
    date_pair = (dt.date(2021, 7, 8), dt.date(2021, 7, 12))
    time_pair = (dt.time(6, 00), dt.time(22, 00))
    table = Table(data, name, date_pair, time_pair)
    table.visualize()

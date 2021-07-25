from collections import namedtuple
import dataclasses
import datetime as dt
import re
from typing import Optional, Union

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from slack_bolt import Ack
from slack_sdk import WebClient

from blocks import read_json
from blocks.answer import AnswerModal
from settings import set_logger

# TODO: デバッグ用で開発後には削除する
from pprint import pprint


logger = set_logger(__name__)
PATTERN = 2


def open_modal(ack: Ack, body: dict, client: WebClient):
    """回答用 Modal を表示する．"""

    view_json = read_json("./modals/answer_schedule.json")
    view_json["blocks"], time = insert_block(body)

    ack()

    client.views_open(
        trigger_id=body["trigger_id"],
        view=view_json)


def insert_block(body: dict) -> list:
    """回答用 Modal のブロックを編集する．"""

    insert_blocks = []
    values = {}

    # [主催者、日、時間、設定] をメッセージから取得する
    items = ['host', 'date', 'time', 'setting']
    for item in body["message"]["blocks"]:
        if "block_id" in item and item["block_id"] in items:
            values[item["block_id"]] = item["text"]["text"].split("\n")[1]

    # 開催日から終了日の間 の日付を生成する
    dates = values["date"].split(" から ")
    values["date"] = [str(item.date()) for item in pd.date_range(dates[0], dates[1])]

    # 時間選択 のブロック
    for item in values["date"]:
        insert_blocks.extend(generate_block(item, values["time"], 1))

    # 主催者宛 のブロック
    users_json = generate_description_block(body["actions"][-1]["value"])
    insert_blocks.extend(users_json)

    return insert_blocks, values["time"]


def generate_block(date: str, time: str, num: int) -> list:
    """回答用 Modal のブロックを追加する．"""

    divider_block = {"type": "divider"}

    if PATTERN == 1:
        # Pattern 1
        pattern = [divider_block, generate_date_block(date, time),
                   generate_time_block(date, time, num), generate_buttons_block(date, "None")]
    elif PATTERN == 2:
        # Pattern 2
        modal = AnswerModal(date, time)  # FIXME
        pattern = [divider_block, modal.date_input_block,
                   generate_buttons_block(date)]

    return pattern


def generate_date_block(date: str, time: str) -> dict:
    """Pattern1 回答用 Modal の日にちのブロックを追加する．"""

    date_block = read_json("./answer/add_date.json")
    date_block["block_id"] = date
    date_block["text"]["text"] = date_block["text"]["text"].replace("date", date).replace("time", time)
    date_block["accessory"]["value"] += f"-{date}"

    return date_block


def generate_date_section_block(date: str, time: str, initial: str) -> dict:
    """Pattern2 回答用 Modal の日にちのSectionブロックを追加する．"""

    label_json = read_json("./answer/add_date-section.json")

    label_json["block_id"] = date
    label_json["text"]["text"] = label_json["text"]["text"].replace("date", date).replace("time", time).replace("opt", initial)

    return label_json


def generate_time_block(date: str, time: str, num: int) -> dict:
    """Pattern1 回答用 Modal の時間選択のブロックを追加する．"""

    start_time, end_time = time.split(" から ")

    time_block = read_json("./answer/add_time.json")
    time_block["block_id"] = time_block["block_id"].replace("date", date).replace("opt", str(num))
    time_block["elements"][0]["initial_time"] = start_time
    time_block["elements"][1]["initial_time"] = end_time

    return time_block


def generate_buttons_block(date: str, value="default") -> dict:
    """Pattern2 回答用 Modal の時間選択のブロックを追加する．"""

    option_json = read_json("./answer/add_button_options.json")
    option_json["block_id"] = f"{date}-opt"
    if value == "yes":
        option_json["elements"][0]["style"] = "primary"
    elif value == "no":
        option_json["elements"][-1]["style"] = "danger"

    return option_json


def generate_description_block(value: str) -> dict:
    """回答用 Modal の作者のブロックを追加する．"""

    if PATTERN == 1:
        # Pattern 1
        host_json = read_json("./answer/add_host.json")
        host_json["value"] = value

        description_json = read_json("./answer/add_user.json")
        description_json[-1]["element"]["initial_option"] = host_json
        description_json[-1]["element"]["options"].append(host_json)
    elif PATTERN == 2:
        # Pattern 2
        description_json = [read_json("./answer/add_description.json")]
        description_json[0]["elements"][0]["text"] += f"<@{value.split('-')[1]}>"
        description_json[0]["elements"][1]["alt_text"] = value

    return description_json


def update_modal(ack: Ack, body: dict, client: WebClient):
    """回答用 Modal のブロックを更新する．"""

    view_json = read_json("./modals/answer_schedule.json")
    view_json["blocks"] = body["view"]["blocks"]
    target = body["actions"][0]["block_id"]
    action = body["actions"][0]["action_id"]

    if PATTERN == 1:
        # 時間設定のブロック を追加する
        if action == "member-add_date":
            target_blocks = insert_time_block(body)

        # 入力した時間 に設定する
        else:
            target_blocks = update_time_input(body)

        view_json["blocks"] = target_blocks

    elif PATTERN == 2:
        if "click_option" in action:

            button_select = action.split('-')[-1]
            date = target.removesuffix("-opt")

            for index, item in enumerate(view_json["blocks"]):
                if item["block_id"] == target:

                    value = view_json["blocks"][index-1]

                    condition = True
                    if value["type"] == "section":
                        text = value["text"]["text"].split('*')
                        current_input, time = text[-2], text[3]
                        condition = (
                            (current_input == "終日可能" and button_select == "no") or
                            (current_input == "参加不可能" and button_select == "yes"))
                    else:
                        time = value["label"]["text"].split(" の ")[-1]

                    view_json["blocks"][index-1] = update_date_block(condition, value["block_id"], time, button_select)
                    item["elements"] = update_button_block(condition, date, button_select)

                    break

    ack()

    # モーダルを 更新する
    client.views_update(
        view=view_json,
        hash=body["view"]["hash"],
        view_id=body["view"]["id"])


def insert_time_block(body: dict) -> dict:
    """Pattern1 回答用 Modal の時間選択ブロックを追加更新する．"""

    target_date = body["actions"][0]["block_id"]
    temp = body["view"]["blocks"]

    target_blocks = [item for item in temp
                     if "block_id" in item and target_date in item["block_id"]]

    option_num = len(target_blocks)
    option_time = str(target_blocks[0]["text"]["text"].split("の")[-1].strip(' *'))

    for i in range(len(temp)):
        if target_date in temp[i]["block_id"]:
            temp.insert(i+2, generate_time_block(target_date, option_time, option_num))
            break

    return temp


def update_date_block(check: bool, date: str, time: str, value: str):
    """Pattern2 回答用 Modal の時間回答ブロックを追加更新する．"""

    if not check:
        return AnswerModal(date, time).date_input_block

    update_value = "終日可能" if value == "yes" else "参加不可能"
    return generate_date_section_block(date, time, update_value)


def update_button_block(check: bool, date: str, button_select: str):
    """Pattern2 回答用 Modal のボタンブロックを追加更新する．"""

    if check:
        return generate_buttons_block(date, button_select)["elements"]
    else:
        return generate_buttons_block(date)["elements"]


def update_time_input(body: dict) -> dict:
    """Pattern1 回答用 Modal の時間選択ブロックを更新する．"""

    # TODO: 入力した時間が有効か確認する
    # TODO: 重複しているか確認

    return body["view"]["blocks"]


def get_modal_inputs(body: dict, values: dict) -> dict:
    """回答用 Modal の 入力を取得する．"""

    member = body["user"]["id"]
    target = body["view"]["blocks"][-1]["elements"][0]["text"].split(':')[-1]
    secret = body["view"]["blocks"][-1]["elements"][1]["alt_text"]
    dates, date = {}, "date"

    # 入力した日時を取得する
    if PATTERN == 1:
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
                sets = [temp["member_start-timepicker-action"]["selected_time"],
                        temp["member_end-timepicker-action"]["selected_time"]]

            dates[date].append(sets)

    elif PATTERN == 2:
        # Pattern 2
        for item in values:
            dates[item] = values[item]["plain_text_input-action"]["value"]

    return {
        "target": target,
        "secret_value": secret,
        "available_date": dates,
        "member": member
    }


def get_message(value: str, client: WebClient):
    """主催者の スケージュール調整詳細メッセージ を取得する"""

    target_channel, host, post_time = value.split('-')

    # Target message
    message_list = client.conversations_history(
        channel=target_channel,
        oldest=post_time,
        inclusive=True,
        limit=1)["messages"]

    if message_list == []:
        return None

    message_info = message_list[0]
    target_message = message_info["ts"]

    result = {"channel": target_channel}

    # スレッドの確認
    thread_present = False
    if "thread_ts" in message_info:
        thread_present = True

        reply_content = client.conversations_replies(
            channel=target_channel,
            ts=message_info["thread_ts"],
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
    inputs = get_modal_inputs(body, values)
    secret_value = inputs["secret_value"]

    ack()

    # メッセージを送信する
    send_answer(inputs, secret_value, client)


def send_answer(inputs: dict, secret_value: str, client: WebClient):
    """回答用 Modal の提出を確認メッセージを送信する．"""

    # スケジュール調整の詳細メッセージスレッドを取得
    result = get_message(secret_value, client)

    message_json = read_json("./message/from_member-yes.json")
    message_json[0]["text"]["text"] = message_json[0]["text"]["text"].replace("I", f"<@{inputs['member']}>")

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
    print("\n\nモーダルの入力")
    pprint({"result": inputs['available_date']})


def send_not_answer(ack: Ack, body: dict, client: WebClient):
    """参加できない と主催者に送信する．"""

    member = body["user"]["id"]
    secret_value = body["actions"][0]["value"]

    # スケジュール調整の詳細メッセージスレッドを取得
    result = get_message(secret_value, client)

    message_json = read_json("./message/from_member-no.json")
    message_json[0]["text"]["text"] = message_json[0]["text"]["text"].replace("I", f"<@{member}>")

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
            channel=target_channel,
            text="メッセージを確認してください",
            blocks=input_block,
            ts=target_message,
            as_user=True)
    else:
        client.chat_postMessage(
            channel=target_channel,
            text="メッセージを確認してください",
            blocks=input_block,
            thread_ts=target_message,
            as_user=True)


def register(app):
    logger.info("register")

    # メッセージのクリック時
    app.action("answer_schedule")(open_modal)
    app.action("not_answer")(send_not_answer)

    # 「追加」ボタンのクリック時
    app.action("member-add_date")(update_modal)

    # 時間の選択時
    app.action("member_start-timepicker-action")(update_modal)
    app.action("member_end-timepicker-action")(update_modal)
    app.action("member_check-action")(update_modal)

    app.action("click_option-yes")(update_modal)
    app.action("click_option-no")(update_modal)

    # 提出時
    app.view("answer_schedule")(check_modal)


##########################################
# utilities
##########################################

StartEnd = namedtuple('StartEnd', ['start', 'end'])


@dataclasses.dataclass
class Table:
    data: dataclasses.InitVar[dict]
    name: str
    date_pair: Union[tuple[dt.date, dt.date], StartEnd]
    time_pair: Union[tuple[dt.time, dt.time], StartEnd]
    df: dataclasses.InitVar[Optional[pd.DataFrame]] = None

    slots: list = dataclasses.field(init=False, default_factory=list)

    def __post_init__(self, data, df):
        self.date_pair = StartEnd(*self.date_pair)
        start, end = self.time_pair
        self.time_pair = StartEnd(start.replace(minute=0), end)
        for date, text in data.items():
            self.slots.extend(self.input_to_datetime(date, text))

        if isinstance(df, pd.DataFrame):
            self.df = self.update_df(df)
        else:
            self.df = self.create_df()

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

    def create_df(self):
        """空いている時間の表を作成する．"""
        start = dt.datetime.combine(self.date_pair.start, self.time_pair.start)
        end = dt.datetime.combine(self.date_pair.end, self.time_pair.end)

        index = pd.date_range(start, end, freq=dt.timedelta(minutes=30))
        df = pd.DataFrame({self.name: False}, index=index)
        df.columns.set_names("name", inplace=True)
        for s, e in self.slots:
            df.loc[s:e, self.name] = True  # TODO: `-6:01`という回答が`6:00-6:30`と解釈される．
        return df

    def update_df(self, df: pd.DataFrame):
        df[self.name] = False
        for s, e in self.slots:
            df.loc[s:e, self.name] = True
        return df

    def visualize(self):
        # TODO: レイアウトの調整
        table = self.table
        # w = len(table.columns)
        # figsize = np.array(table.T.shape) * 10.5 / w
        dates = table.index.get_level_values("date").unique()
        _, axes = plt.subplots(nrows=dates.size, sharex=True)
        for i, (ax, date) in enumerate(zip(axes, dates)):
            g = sns.heatmap(table.loc[(date, slice(None))],
                            ax=ax, square=True,
                            cbar=False, cmap=["white", "lightblue", "lightgreen"],
                            linecolor="grey", linewidths=0.2)
            g.set_title(date)
            g.set(xlabel=None, ylabel=None)
            g.tick_params(bottom=False, left=False, right=False, top=False)
        g.set_xticklabels(table.columns.map(lambda t: str(t.hour) if t.minute == 0 else ""),
                          rotation=0)
        plt.tight_layout()
        plt.show()
        # plt.savefig(f"{TMP_DIR}/table.png")

    @property
    def table(self):
        df = self.df
        df.set_index([df.index.date, df.index.time], inplace=True)
        df.index.set_names(["date", "time"], inplace=True)

        start, end = self.time_pair
        table = df.unstack(level="time").stack(level="name").loc[:, start:end]
        return table.astype(int) + table.groupby(level="date").all()


if __name__ == "__main__":
    host_setting = dict(date_pair=(dt.date(2021, 7, 8), dt.date(2021, 7, 12)),
                        time_pair=(dt.time(6, 00), dt.time(22, 00)))
    table1 = Table(data={dt.date(2021, 7, 10): '7 : 00 -11 : 00, 14:30  ~ 21:00'},
                   name="one", **host_setting)
    table2 = Table(data={dt.date(2021, 7, 10): '6 : 00 -6 : 45, 14:30  ~ 18:00'},
                   name="two", **host_setting, df=table1.df)
    tmp = table2.convert_to_table()

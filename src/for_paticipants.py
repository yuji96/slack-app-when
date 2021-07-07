import datetime as dt
import re

import pandas as pd

from blocks import read_json
from settings import set_logger


logger = set_logger(__name__)


# TODO: チュートリアルの関数なので将来的に削除する
def update_home_tab(client, event, logger):
    logger.info("open")
    blocks = read_json("home.json")
    blocks[0]["text"]["text"] = str(dt.datetime.now())
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


def register(app):
    logger.info("register")
    app.event("app_home_opened")(update_home_tab)


##########################################
# utilities
##########################################


class Table:
    def __init__(self, text: str, start=dt.datetime(2021, 5, 11, 8, 0), end=dt.datetime(2021, 5, 11, 12, 40), name: str=None):
        self.name = name

        self.slots = self.input_to_datetime(text)
        self.table = self.create_time_table(start, end)

    @staticmethod
    def input_to_datetime(text, date="2021/05/11"):  # TODO: dateは仮
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
        text = re.sub(r"\s*([:\-~,])\s*", r"\1", text)
        str_slots = text.split(",")
        dt_slots = []

        for str_start, str_end in map(lambda slot: re.split(r"[\-~]", slot), str_slots):
            start = dt.datetime.strptime(date + str_start, "%Y/%m/%d%H:%M")  # TODO: ゼロ埋めの有無でエラーが出るか確認
            end = dt.datetime.strptime(date + str_end, "%Y/%m/%d%H:%M")
            if end <= start:
                raise ValueError(f"`{str_start}-{str_end}` の入力が正しくありません。")
            dt_slots.append((start, end))

        return dt_slots

    def create_time_table(self, start: dt.datetime, end: dt.datetime):
        """空いている時間の表を作成する．

        Examples
        --------
        >>> table = Table('9:00-11:00, 14:30~18:10')
        >>> tmp = table.create_time_table(start=dt.datetime(2021, 5, 11, 8, 0), end=dt.datetime(2021, 5, 11, 12, 40))
        >>> tmp.to_list()
        [False, False, True, True, True, True, False, False, False, False]
        
        """
        # TODO: 強制的に30分区切りにする処理を追加する．
        # TODO: multiindex 化したい．
        table = pd.Series(data=False, index=pd.date_range(start, end, freq=dt.timedelta(minutes=30), closed="left"))
        for s, e in self.slots:
            table[s:e - dt.timedelta(minutes=1)] = True
        return table

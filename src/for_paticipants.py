import dataclasses
import datetime as dt
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from blocks import read_json
from settings import set_logger, TMP_DIR


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

        stack = pd.Series(single.values, index=[index.date, index.time])
        table = stack.unstack().loc[:, start.time():end.time()]
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

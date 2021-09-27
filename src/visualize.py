from collections import namedtuple
import datetime as dt
import io
import pickle
import re

import matplotlib
import pandas as pd
import requests
import seaborn as sns

from settings import TMP_DIR

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa

StartEnd = namedtuple('StartEnd', ['start', 'end'])


class Table:
    def __init__(self, answer, name, date_pair, time_pair, client,
                 df=None, file_url=None):
        self.name = name
        self.date_pair = StartEnd(*[dt.datetime.strptime(d, "%Y-%m-%d").date() for d in date_pair])
        start, end = [dt.datetime.strptime(t, "%H:%M").time() for t in time_pair]
        self.time_pair = StartEnd(start.replace(minute=0), end)
        self.client = client

        self.slots = []  # TODO: yield from?
        for date, text in answer.items():
            # TODO: datetimeへの型変換のリファクタが必要
            date = dt.datetime.strptime(date, "%Y-%m-%d").date()
            self.slots.extend(self.input_to_datetime(date, text))

        if df is not None:
            self.df = self.update_df(df)
        elif file_url:
            self.df = self.download(file_url)
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

    def visualize(self, debug=False):
        # TODO: レイアウトの調整
        table = self.table
        # w = len(table.columns)
        # figsize = np.array(table.T.shape) * 10.5 / w
        dates = table.index.get_level_values("date").unique()
        fig, axes = plt.subplots(nrows=dates.size, sharex=True)
        for i, (ax, date) in enumerate(zip(axes, dates)):
            # TODO: 最小値 == white ではなく、0 == white にする。
            g = sns.heatmap(table.loc[(date, slice(None))],
                            ax=ax, square=True,
                            cbar=False, cmap=["white", "lightblue", "lightgreen"],
                            linecolor="grey", linewidths=0.2)
            g.set_title(date)
            g.set(xlabel=None, ylabel=None)
            g.tick_params(bottom=False, left=False, right=False, top=False)
        # TODO: ばぐってる
        # g.set_xticklabels(table.columns.map(lambda t: str(t.hour) if t.minute == 0 else ""),
        #                   rotation=0)
        plt.tight_layout()
        if debug:
            plt.show()
        else:
            stream = io.BytesIO()
            plt.savefig(stream, format="png")
            plt.close(fig)
            return stream.getvalue()

    @property
    def table(self):
        df = self.df
        df.set_index([df.index.date, df.index.time], inplace=True)
        df.index.set_names(["date", "time"], inplace=True)

        start, end = self.time_pair
        table = df.unstack(level="time").stack(level="name").loc[:, start:end]
        return table.astype(int) + table.groupby(level="date").all()

    def download(self, file_url):
        res = requests.get(file_url, headers=dict(Authorization=f"Bearer {self.client.token}"))
        assert res.status_code == 200
        return self.update_df(pickle.loads(res.content))

    def upload(self, channels):
        # TODO: 中間ファイルがないのが理想 import tempfile
        self.df.to_pickle(f"{TMP_DIR}/table.pkl")
        res = self.client.files_upload(channels=channels, file=f"{TMP_DIR}/table.pkl")
        return res["file"]["id"]


if __name__ == "__main__":
    host_setting = dict(date_pair=(dt.date(2021, 7, 8), dt.date(2021, 7, 12)),
                        time_pair=(dt.time(6, 00), dt.time(22, 00)))
    table1 = Table(answer={dt.date(2021, 7, 10): '7 : 00 -11 : 00, 14:30  ~ 21:00'},
                   name="one", **host_setting)
    table1.to_pickle()

    df = pd.read_pickle(f"{TMP_DIR}/pickle.pkl")
    table2 = Table(answer={dt.date(2021, 7, 10): '6 : 00 -6 : 45, 14:30  ~ 18:00'},
                   name="two", **host_setting, df=df)
    table2.visualize()

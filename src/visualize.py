from collections import namedtuple
import dataclasses
import datetime as dt
import re
from typing import Optional, Union

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


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

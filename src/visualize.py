from collections import namedtuple
import datetime as dt
import io
import pickle

import matplotlib
import pandas as pd
import requests
import seaborn as sns

from scheduler.slack_parser import AnswerFormData
from settings import TMP_DIR

matplotlib.use('agg')
import matplotlib.pyplot as plt  # noqa

StartEnd = namedtuple('StartEnd', ['start', 'end'])


class Table:
    def __init__(self, answer: AnswerFormData, name,
                 client=None, df=None, file_url=None):
        # TODO: tmp code
        date_pair = answer._date_pair
        time_pair = answer._time_pair
        self.slots = answer.slots

        self.name = name
        self.date_pair = StartEnd(*[dt.datetime.strptime(d, "%Y-%m-%d").date() for d in date_pair])
        start, end = [dt.datetime.strptime(t, "%H:%M").time() for t in time_pair]
        self.time_pair = StartEnd(start.replace(minute=0), end)
        self.client = client

        if df is not None:
            self.df = self.update_df(df)
        elif file_url:
            self.df = self.download(file_url)
        else:
            self.df = self.create_df()

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
        fig, axes = plt.subplots(nrows=dates.size)
        for i, (ax, date) in enumerate(zip(axes, dates)):
            g = sns.heatmap(table.loc[(date, slice(None))],
                            ax=ax, square=True,
                            cbar=False, cmap=["white", "lightblue", "lightgreen"], vmin=0, vmax=2,
                            linecolor="grey", linewidths=0.2)
            g.set_title(date)
            g.set(xlabel=None, ylabel=None)
            g.tick_params(bottom=False, left=False, right=False, top=False)
            # FIXME: remove magic number
            g.set_xticks(range(35))
            g.set_xticklabels(table.columns.map(lambda t: str(t.hour) if t.minute == 0 else ""),
                              rotation=0)
            g.vlines(range(35)[::2], *g.get_ylim(), colors="k", lw=0.3)
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
    matplotlib.use('macOSX')
    import matplotlib.pyplot as plt  # noqa

    host_setting = dict(date_pair=("2021-07-08", "2021-07-12"),
                        time_pair=("06:00", "23:00"))
    table1 = Table(name="Mercury", answer=AnswerFormData(
        answer={"2021-07-10": '7 : 00 -11 : 00, 14:30  ~ 21:00'}, **host_setting))
    table2 = Table(name="Venus", df=table1.df, answer=AnswerFormData(
        answer={"2021-07-10": '6 : 00 -6 : 45, 14:30  ~ 18:00'}, **host_setting))
    table3 = Table(name="Earth", df=table2.df, answer=AnswerFormData(
        answer={"2021-07-10": '6 : 30 -8 : 50, 12:00  ~ 15:00'}, **host_setting))
    table3.visualize(debug=True)

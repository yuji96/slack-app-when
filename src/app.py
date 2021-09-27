from slack_bolt import App

from scheduler import private
import settings
from settings import set_logger


logger = set_logger(__name__)
app = App(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET,
    logger=logger,
)

private.register(app)

# HACK: 毎回必要な変数はos.environに設定するのが良いかも


# TODO: スレッドごと消したい
@app.event("reaction_added")
def ask_for_introduction(event, *args, **kwargs):
    print(event["item_user"])
    if (event["reaction"] == "put_litter_in_its_place"
            and event["item_user"] == settings.SLACK_BOT_ID):
        app.client.chat_delete(channel=event["item"]["channel"],
                               ts=event["item"]["ts"])


app.start(port=settings.PORT)

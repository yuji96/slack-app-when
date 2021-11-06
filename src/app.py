from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

from scheduler import common, im, channel
import settings
from settings import set_logger


logger = set_logger(__name__)
app = App(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET,
    logger=logger,
)
# HACK: 毎回必要な変数はos.environに設定するのが良いかも

common.register(app)
im.register(app)
channel.register(app)


# HACK: スレッドごと消したい
@app.event("reaction_added")
def ask_for_introduction(event, *args, **kwargs):
    if (event["reaction"] == "put_litter_in_its_place"
            and event["item_user"] == settings.SLACK_BOT_ID):
        app.client.chat_delete(channel=event["item"]["channel"],
                               ts=event["item"]["ts"])


flask_app = Flask(__name__)
handler = SlackRequestHandler(app)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@flask_app.route("/")
def hello():
    return "Hello, World!"


if __name__ == "__main__":
    # app.start(port=settings.PORT)
    flask_app.run(host="0.0.0.0", port=settings.PORT)

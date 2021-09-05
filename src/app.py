from slack_bolt import App

import for_host
import for_member
import settings
from settings import SLACK_BOT_ID, set_logger


logger = set_logger(__name__)
app = App(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET,
    logger=logger,
)

for_host.register(app)
for_member.register(app)


# TODO: スレッドごと消したい
@app.event("reaction_added")
def ask_for_introduction(event, *args, **kwargs):
    if event["reaction"] == "put_litter_in_its_place" and event["item_user"] == SLACK_BOT_ID:
        app.client.chat_delete(channel=event["item"]["channel"],
                               ts=event["item"]["ts"])


app.start(port=settings.PORT)

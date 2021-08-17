from slack_bolt import App

import for_host
import for_member
import settings
from settings import set_logger


logger = set_logger(__name__)
app = App(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET,
    logger=logger,
)

for_host.register(app)
for_member.register(app)
app.start(port=settings.PORT)

from slack_bolt import App

import for_manager
import for_paticipants
import settings
from settings import set_logger


logger = set_logger(__name__)
app = App(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET,
    logger=logger,
)

for_manager.register(app)
for_paticipants.register(app)
app.start(port=settings.PORT)

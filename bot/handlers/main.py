import asyncio
from bot import utils, models
from .app import App


def main(session_id: int):
    session = models.UserBotSession.objects.select_related('userbot').get(id=session_id)
    utils.init_logger(session)
    app = App(session)
    asyncio.run(app.start())

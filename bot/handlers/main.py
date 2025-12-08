import asyncio
from bot import utils
from .app import App


def main(phone_number: str, host: bool, func: int):
    utils.init_logger(phone_number)
    app = App(phone_number, host, func)
    asyncio.run(app.start())

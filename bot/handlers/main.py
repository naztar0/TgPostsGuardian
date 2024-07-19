from asyncio import get_event_loop
from bot import utils
from .app import App


def main(number, host=0, func=0):
    utils.init_logger(number)
    app = App(number, host, func)
    get_event_loop().run_until_complete(app.start())

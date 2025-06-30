import asyncio
from telegram.ext import Application
from . import config
from .worker import search_worker

async def post_init(app: Application):
    config.search_queue = asyncio.Queue()
    app.create_task(search_worker(app))

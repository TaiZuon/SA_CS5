import asyncio
import aiohttp
import logging
from main_app import config
from main_app.database import reset_db
from main_app.controller import collect_data
from prometheus_client import start_http_server
from sidecar.log_writing import setup_logging

setup_logging()

async def main():
    start_http_server(8000)
    reset_db()
    async with aiohttp.ClientSession() as session:
        await collect_data(session)

if __name__ == "__main__":
    import time
    start = time.time()

    asyncio.run(main())
    print(f"⏱️ Tổng thời gian: {time.time() - start:.2f} giây")

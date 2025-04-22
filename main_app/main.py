import asyncio
import aiohttp
import logging
from main_app.database import reset_db
from main_app.process import collect_data
from sidecar.log_writing import setup_logging
from sidecar.metric_server import start_metrics_server 

setup_logging()

async def main():
    reset_db()

    start_metrics_server(port=8000, update_interval=5)

    async with aiohttp.ClientSession() as session:
        await collect_data(session, 5000)

if __name__ == "__main__":
    import time
    start = time.time()
    logging.info("🌐 Bắt đầu chương trình...")
    asyncio.run(main())
    logging.info(f"⏱️ Tổng thời gian: {time.time() - start:.2f} giây")

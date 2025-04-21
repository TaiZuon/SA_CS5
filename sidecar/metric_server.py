from prometheus_client import start_http_server, Summary, Counter, Gauge
import asyncio
import psutil
import logging
import os

REQUEST_TIME = Summary('request_processing_seconds', 'Thời gian xử lý repo')
REPOS_PROCESSED = Counter('repos_processed_total', 'Tổng số repo đã xử lý')
ACTIVE_TASKS = Gauge('active_tasks', 'Số lượng task đang chạy')
ERROR_COUNT = Counter('errors_total', 'Tổng số lỗi xảy ra')

# Metric cho việc sử dụng CPU và RAM
CPU_USAGE = Gauge('cpu_usage_percent', 'Tỉ lệ phần trăm sử dụng CPU')
RAM_USAGE = Gauge('ram_usage_mb', 'Dung lượng RAM sử dụng (MB)')

async def update_system_metrics():
    """Cập nhật các chỉ số CPU và RAM"""
    # Lấy tỉ lệ sử dụng CPU (tính theo phần trăm)
    cpu_percent = psutil.cpu_percent(interval=1)
    CPU_USAGE.set(cpu_percent)
    logging.info(f"CPU Usage: {cpu_percent}%")

    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / (1024 * 1024)
    RAM_USAGE.set(mem_mb)  # Chuyển đổi sang MB
    logging.info(f"RAM Usage: {mem_mb:.2f}MB")

async def metrics_updater(interval=5):
    """Hàm chạy định kỳ để cập nhật metric"""
    while True:
        await update_system_metrics()
        await asyncio.sleep(interval)  # Cập nhật sau mỗi `interval` giây

async def start_metrics_server(port=8000, update_interval=5):
    """Khởi động server và cập nhật metric định kỳ"""
    start_http_server(port)

    await metrics_updater(update_interval) 

    logging.info(f"Prometheus Metrics Server is running at http://localhost:{port}")

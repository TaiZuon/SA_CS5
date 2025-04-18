import logging
import os
from datetime import datetime
import psutil  # Thêm thư viện để đo tài nguyên hệ thống
import time

def setup_logging():
    # Tạo thư mục logs nếu chưa tồn tại
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Tạo tên file log theo dấu thời gian
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(log_dir, f"{timestamp}.txt")

    # Cấu hình logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()  # Ghi log ra console
        ]
    )

    logging.info(f"Logging initialized. Logs will be saved to {log_file}")

def log_resource_usage(stage):
    """
    Ghi log mức sử dụng CPU và RAM tại một công đoạn cụ thể.
    Args:
        stage (str): Tên công đoạn để log
    """
    process = psutil.Process()
    cpu_percent = psutil.cpu_percent(interval=0.1)  # Lấy % CPU sử dụng
    memory_info = process.memory_info()
    ram_usage_mb = memory_info.rss / (1024 * 1024)  # Chuyển đổi RAM sang MB
    logging.info(f"[{stage}] CPU: {cpu_percent}% | RAM: {ram_usage_mb:.2f} MB")

def log_timing(stage, start_time, count=None, unit="items"):
    """
    Ghi log thời gian thực hiện một công đoạn và số lượng dữ liệu xử lý.
    Args:
        stage (str): Tên công đoạn để log
        start_time (float): Thời gian bắt đầu (time.time())
        count (int, optional): Số lượng dữ liệu xử lý
        unit (str, optional): Đơn vị của dữ liệu (mặc định là "items")
    """
    elapsed_time = time.time() - start_time
    if count is not None:
        logging.info(f"[{stage}] Hoàn thành trong {elapsed_time:.2f} giây, xử lý {count} {unit}.")
    else:
        logging.info(f"[{stage}] Hoàn thành trong {elapsed_time:.2f} giây.")
import asyncio
import logging
import os
from datetime import datetime
import matplotlib
import psutil  # Thêm thư viện để đo tài nguyên hệ thống
import time
import matplotlib.pyplot as plt 

resource_data = []
timing_data = []

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
    resource_data.append({"stage": stage, "cpu": cpu_percent, "ram": ram_usage_mb, "time": time.time()})
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
    timing_data.append({"stage": stage, "elapsed_time": elapsed_time, "count": count, "unit": unit})
    if count is not None:
        logging.info(f"[{stage}] Hoàn thành trong {elapsed_time:.2f} giây, xử lý {count} {unit}.")
    else:
        logging.info(f"[{stage}] Hoàn thành trong {elapsed_time:.2f} giây.")

async def track_resource_usage():
    """
    Theo dõi mức tiêu thụ CPU và RAM theo từng giây.
    """
    while True:
        process = psutil.Process()
        cpu_percent = psutil.cpu_percent(interval=1)  # Lấy % CPU sử dụng mỗi giây
        memory_info = process.memory_info()
        ram_usage_mb = memory_info.rss / (1024 * 1024)  # Chuyển đổi RAM sang MB
        resource_data.append({
            "time": time.time(),
            "cpu": cpu_percent,
            "ram": ram_usage_mb
        })
        logging.info(f"[Theo dõi tài nguyên] CPU: {cpu_percent}% | RAM: {ram_usage_mb:.2f} MB")
        await asyncio.sleep(1)  # Chờ 1 giây trước khi ghi tiếp

def plot_metrics():
    """
    Vẽ đồ thị tiêu thụ CPU và RAM theo thời gian.
    """
    # Dữ liệu CPU và RAM theo thời gian
    times = [d["time"] - resource_data[0]["time"] for d in resource_data]  # Tính thời gian từ giây đầu tiên
    cpu_usage = [d["cpu"] for d in resource_data]
    ram_usage = [d["ram"] for d in resource_data]

    plt.figure(figsize=(12, 6))

    # Vẽ đồ thị CPU
    plt.plot(times, cpu_usage, label="CPU Usage (%)", color="blue")
    plt.plot(times, ram_usage, label="RAM Usage (MB)", color="green")

    # Ghi nhãn giá trị CPU và RAM trên đồ thị
    # for i, (time_point, cpu, ram) in enumerate(zip(times, cpu_usage, ram_usage)):
    #     plt.text(time_point, cpu, f"{cpu:.1f}%", fontsize=8, ha="center", va="bottom", color="blue")
    #     plt.text(time_point, ram, f"{ram:.1f} MB", fontsize=8, ha="center", va="bottom", color="green")

    plt.title("CPU and RAM Usage Over Time")
    plt.xlabel("Time (s)")
    plt.ylabel("Usage")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()
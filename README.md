# GitHub Data Collector

## Thông tin nhóm

- **Nhóm**: 1
- **Lớp học phần**: INT3105 1
- **Sinh viên**:
  - Thân Việt Anh - 22026503
  - Ngô Quốc An - 22026515
  - Nguyễn Thái Dương - 22026533

---

## Mô tả dự án

Hệ thống thu thập dữ liệu từ GitHub bao gồm thông tin repository, release và commit của top 5000 repo theo Gitstar Ranking. Hệ thống hỗ trợ:

- Fetch dữ liệu theo thứ tự: repo → release → commit
- Sử dụng API `/compare/{base}...{head}` để lấy commit giữa hai release
- Ghi log thời gian, tài nguyên, trạng thái xử lý
- Có thể lưu dữ liệu vào database hoặc xuất thành file SQL
- Hỗ trợ retry, cooldown token, theo dõi metric qua Prometheus

# Hướng Dẫn Cài Đặt và Chạy Chương Trình

## I. Set up

### 1. Cài Đặt Cơ Sở Dữ Liệu (MySQL)

1. Cài đặt MySQL (nếu chưa cài đặt).
2. Tạo cơ sở dữ liệu và nhập schema từ file `db.sql`:
   ```bash
   mysql -u root -p < db.sql
   ```

### 2. Cài Đặt Python

1. Cài đặt Python 3.10 trở lên từ [Python official site](https://www.python.org/downloads/).
2. Cài đặt và sử dụng `venv` để tạo môi trường ảo (virtual environment):
   - Trên **macOS/Linux**:
     ```bash
     python3.10 -m venv venv
     source venv/bin/activate
     ```
   - Trên **Windows**:
     ```bash
     python3.10 -m venv venv
     .\venv\Scripts\activate
     ```
3. Cài đặt các phụ thuộc:
   ```bash
   pip install -r requirements.txt
   ```

### 6. Cài Đặt Prometheus

#### Trên **macOS/Linux**:

1. Tải Prometheus từ [trang chính của Prometheus](https://prometheus.io/download/).
   ```bash
   # Ví dụ cho macOS/Linux (tùy theo hệ điều hành, có thể thay đổi link tải)
   wget https://github.com/prometheus/prometheus/releases/download/v2.29.1/prometheus-2.29.1.darwin-amd64.tar.gz
   tar -xvzf prometheus-2.29.1.darwin-amd64.tar.gz
   cd prometheus-2.29.1.darwin-amd64
   ```
2. Cấu hình `prometheus.yml` như sau:
   ```yaml
   scrape_configs:
     - job_name: "python_app"
       static_configs:
         - targets: ["localhost:8000"]
   ```
3. Chạy Prometheus:
   ```bash
   ./prometheus --config.file=prometheus.yml
   ```

#### Trên **Windows**:

1. Tải Prometheus từ [trang chính của Prometheus](https://prometheus.io/download/).
   - Giải nén file và di chuyển đến thư mục chứa file `prometheus.exe`.
2. Cấu hình `prometheus.yml` như sau:
   ```yaml
   scrape_configs:
     - job_name: "python_app"
       static_configs:
         - targets: ["localhost:8000"]
   ```
3. Chạy Prometheus:
   - Mở Command Prompt và di chuyển đến thư mục chứa file `prometheus.exe`:
     ```cmd
     cd C:\path\to\prometheus
     prometheus.exe --config.file=prometheus.yml
     ```

### 7. Cài Đặt Grafana

1. Cài đặt Grafana từ [trang chính của Grafana](https://grafana.com/get).
2. Sau khi cài đặt xong, truy cập vào Grafana tại `http://localhost:3000` (mặc định username và password là `admin`).
3. Thêm nguồn dữ liệu Prometheus:
   - Truy cập `Configuration` → `Data Sources`.
   - Chọn Prometheus, nhập URL: `http://localhost:9090` và lưu lại.
4. Tạo dashboard mới và sử dụng các metric đã cấu hình trong Prometheus để theo dõi ứng dụng.

## II. Chạy Ứng Dụng

1. Tạo file `.env` trong thư mục gốc và điền cấu hình cơ sở dữ liệu cũng như token GitHub:

   ```
   GITHUB_TOKENS=your_github_tokens
   GITHUB_TOKEN=your_single_github_token

   # db config
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=your_database_name
   ```

2. Chạy ứng dụng:

   - Đứng ở thư mục gốc của dự án và chạy lệnh sau:
     ```bash
     python main_app.main
     ```

3. Sau khi ứng dụng chạy, bạn có thể theo dõi các chỉ số trong Prometheus và Grafana.

---

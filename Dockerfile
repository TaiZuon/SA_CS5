# Dockerfile
FROM python:3.10-slim

# Cài các thư viện hệ thống (nếu cần)
RUN apt-get update && apt-get install -y build-essential libffi-dev libssl-dev && rm -rf /var/lib/apt/lists/*
# Tạo thư mục làm việc
WORKDIR /app

# Copy file cần thiết
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . .

# Lệnh mặc định để chạy chương trình
CMD ["python", "main_app/main.py"]

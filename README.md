# 📦 Github Data Collector

Dự án thu thập thông tin các repo nổi bật từ GitHub (stars > 1000), lưu release và commit tương ứng vào MySQL.

## ✅ Mục tiêu

- Thu thập top repo có nhiều sao nhất trên GitHub
- Lưu thông tin release và commit vào MySQL
- Hỗ trợ làm việc nhóm thông qua Docker hoặc setup local

---

## ⚙️ Yêu cầu hệ thống

- Python 3.10+
- Docker (tuỳ chọn)
- Git
- Hệ điều hành: Windows / macOS / Linux

---

## 🐳 Cài đặt MySQL bằng Docker (khuyên dùng)

### Chạy nhanh bằng lệnh `docker run`

```bash
docker run --name mysql-github -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=github_data -p 3306:3306 -d mysql:8.0
```

> ⚠️ Lưu ý: Nếu port 3306 đang bận, bạn có thể đổi sang port khác (ví dụ `-p 3307:3306`).

---

## 🐍 Cài đặt Python Environment

```bash
# Tạo virtual environment
python -m venv venv

# Kích hoạt environment
# Trên Windows:
venv\Scripts\activate

# Trên macOS/Linux:
source venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt
```

---

## 🔐 Cấu hình GitHub Token

Tạo file `.env` cùng cấp với `hello.py`:

```
GITHUB_TOKEN=
```

> 📌 Bạn nên dùng token của riêng mình nếu không muốn giới hạn rate.

---

## 🏃‍♂️ Chạy chương trình

```bash
python hello.py
```

Kết quả:

- Reset database
- Fetch top repo từ GitHub
- Lưu release & commit tương ứng theo từng release vào DB

---

## 🧪 Kiểm tra database

Bạn có thể dùng các công cụ như:

- [MySQL Workbench](https://dev.mysql.com/downloads/workbench/)
- DBeaver
- Kết nối trực tiếp qua `pymysql` hoặc `mysqlclient`

Thông tin kết nối:

```
Host: localhost
Port: 3306
User: root
Password: root
Database: github_data
```

---

## 💬 Ghi chú cho Team

- Docker chi là một lưa chọn.
- Bạn **không cần chia sẻ container**, chỉ cần **sử dụng chung cấu hình** để mỗi người tự tạo container giống nhau.
- Đảm bảo file `.env` được tạo thủ công, không đẩy lên git.
- Token GitHub có thể thay đổi hoặc hết hạn, bạn tự tạo tại: https://github.com/settings/tokens

---

## 🐛 Lỗi thường gặp

| Lỗi                            | Nguyên nhân                               | Giải pháp                                       |
| ------------------------------ | ----------------------------------------- | ----------------------------------------------- |
| `pymysql.err.OperationalError` | Chưa bật MySQL container hoặc sai port    | Kiểm tra `docker ps`, chắc chắn MySQL đang chạy |
| `Data too long for column`     | Commit message quá dài                    | Đã xử lý bằng cắt chuỗi trong code              |
| `Rate limit exceeded`          | Token GitHub không đủ quyền hoặc hết lượt | Dùng token khác                                 |

---

## 👥 Người thực hiện

- ✍️ _nhom 1_

```

```

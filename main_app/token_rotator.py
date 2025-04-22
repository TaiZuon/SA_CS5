import os
import time
import itertools
from dotenv import load_dotenv

load_dotenv()

# Lấy token từ biến môi trường và chuẩn hóa
TOKENS = [t.strip() for t in os.getenv("GITHUB_TOKENS", "").split(",") if t.strip()]
TOKEN_CYCLE = itertools.cycle(TOKENS)

# Map cooldown timestamp cho từng token
cooldown_map = {token: 0 for token in TOKENS}

def mark_token_cooldown(token: str, reset_time_epoch: int):
    """
    Đánh dấu token đang cooldown đến thời điểm reset_time_epoch.
    """
    cooldown_map[token] = reset_time_epoch
    remaining = int(reset_time_epoch - time.time())
    print(f"🕒 Token {token[:10]}... cooldown đến {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(reset_time_epoch))} ({remaining} giây còn lại)")

def get_valid_token() -> str:
    """
    Trả về token hợp lệ chưa bị cooldown.
    Nếu không còn token nào dùng được thì raise Exception.
    """
    for _ in range(len(TOKENS)):
        token = next(TOKEN_CYCLE)
        if time.time() >= cooldown_map.get(token, 0):
            return token
    raise Exception("🚫 Không còn token nào khả dụng, hãy đợi cooldown.")

def is_token_cooldown(token: str) -> bool:
    """
    Trả về True nếu token đang cooldown.
    """
    return time.time() < cooldown_map.get(token, 0)

def wait_until_next_available_token():
    soonest_time = min(cooldown_map.values(), default=0)
    now = time.time()
    wait_time = max(soonest_time - now, 0)
    return wait_time

if __name__ == "__main__":
    print("🔍 Trạng thái cooldown các token:\n")
    now = time.time()
    for token in TOKENS:
        reset_time = cooldown_map.get(token, 0)
        remaining = int(reset_time - now)
        if remaining > 0:
            print(f"⛔ Token {token[:10]}... đang cooldown ({remaining} giây còn lại)")
        else:
            print(f"✅ Token {token[:10]}... sẵn sàng sử dụng")


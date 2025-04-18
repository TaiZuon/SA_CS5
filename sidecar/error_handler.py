import logging
import time
import asyncio
from sidecar.token_rotator import mark_token_cooldown, get_valid_token, wait_until_next_available_token

MAX_RETRY = 1  # Retry nội bộ 1 lần, controller chịu trách nhiệm retry toàn cục
RETRY_DELAY = 2  # giây

async def handle_github_error(resp, token, context=""):
    """
    Phân tích lỗi GitHub API và quyết định có nên dừng hay tiếp tục.
    Trả về True nếu lỗi nghiêm trọng và nên bỏ qua request.
    """
    status = resp.status
    json_body = await resp.json()
    message = json_body.get("message", "No message provided")

    reset_ts = resp.headers.get("X-RateLimit-Reset")
    if reset_ts:
        reset_ts = int(reset_ts)
        now = int(time.time())
        remaining = reset_ts - now
        reset_info = f"⏳ Reset sau {remaining} giây"
    else:
        reset_ts = int(time.time()) + 60
        reset_info = "Không rõ thời gian reset"

    if status == 403:
        logging.warning(f"⚠️ 403 Forbidden tại {context}: {message}. Token {token[:8]}... cooldown. {reset_info}")
        mark_token_cooldown(token, reset_ts)
        return True
    elif status == 401:
        logging.warning(f"❌ 401 Unauthorized tại {context}: Token {token[:8]}... không hợp lệ hoặc hết hạn.")
        mark_token_cooldown(token, reset_ts)
        return True
    elif status == 422:
        logging.warning(f"⚠️ 422 Unprocessable Entity tại {context}: {message}")
        return False
    elif 500 <= status < 600:
        logging.warning(f"🔥 Lỗi server {status} tại {context}: {message}")
        return False
    else:
        logging.warning(f"⚠️ Lỗi {status} tại {context}: {message}")
        return False

async def safe_request(fetch_func, context=""):
    """
    Gọi fetch_func(token) và xử lý lỗi GitHub API. 
    Tự xoay token và retry tối đa 1 lần nếu cần.
    """
    retries = 0
    while retries < MAX_RETRY:
        try:
            token = get_valid_token()
            result = await fetch_func(token)
            if result is not None:
                return result
        except Exception as e:
            logging.warning(f"⚠️ Request lỗi ({context}): {e}")
        retries += 1
        logging.info(f"🔁 Retry {retries}/{MAX_RETRY} ({context})")
        await asyncio.sleep(RETRY_DELAY)

        if retries == MAX_RETRY:
            wait_time = wait_until_next_available_token()
            logging.warning(f"⏸ Đợi {wait_time:.1f}s do hết token khả dụng ({context})")
            await asyncio.sleep(wait_time)

    raise Exception(f"❌ Request thất bại sau {MAX_RETRY} lần ({context})")

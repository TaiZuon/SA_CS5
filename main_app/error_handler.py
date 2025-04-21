import logging
import time
import asyncio
from main_app.token_rotator import mark_token_cooldown, get_valid_token, wait_until_next_available_token
from sidecar.metric_server import ERROR_COUNT

MAX_RETRY = 5
RETRY_DELAY = 2  

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

    ERROR_COUNT.inc()  # Tăng mỗi lần gặp lỗi

    match status:
        case 403:
            logging.warning(f"⚠️ 403 Forbidden tại {context}: {message}. Token {token[:8]}... cooldown. {reset_info}")
            mark_token_cooldown(token, reset_ts)
            return False
        case 401:
            logging.warning(f"❌ 401 Unauthorized tại {context}: Token {token[:8]}... không hợp lệ hoặc hết hạn.")
            mark_token_cooldown(token, reset_ts)
            return False
        case 422:
            logging.warning(f"⚠️ 422 Unprocessable Entity tại {context}: {message}")
            return True  # lỗi nghiêm trọng, bỏ qua request
        case status if 500 <= status < 600:
            logging.warning(f"🔥 Lỗi server {status} tại {context}: {message}")
            return False  # server error, có thể retry
        case _:
            logging.warning(f"⚠️ Lỗi {status} tại {context}: {message}")
            return True  # mặc định bỏ qua request
        
async def safe_request(fetch_func, context=""):
    retries = 0

    while retries < MAX_RETRY:
        token = get_valid_token()
        try:
            resp = await fetch_func(token)

            # Nếu fetch_func trả về response HTTP, kiểm tra lỗi
            if hasattr(resp, 'status') and resp.status >= 400:
                should_skip = await handle_github_error(resp, token, context)
                if should_skip:
                    return None  # Bỏ qua repo này
                else:
                    retries += 1
                    logging.info(f"🔁 Retry {retries}/{MAX_RETRY} ({context})")
                    await asyncio.sleep(RETRY_DELAY)
                    continue

            # Nếu không phải response (fetch_func tự xử lý và trả về JSON chẳng hạn)
            if resp is not None:
                return resp

        except Exception as e:
            logging.warning(f"⚠️ Request lỗi ({context}): {e}")
            retries += 1
            logging.info(f"🔁 Retry {retries}/{MAX_RETRY} ({context})")
            await asyncio.sleep(RETRY_DELAY)

    wait_time = wait_until_next_available_token()
    logging.warning(f"⏸ Đợi {wait_time:.1f}s do hết token khả dụng ({context})")
    await asyncio.sleep(wait_time)

    raise Exception(f"❌ Request thất bại sau {MAX_RETRY} lần ({context})")

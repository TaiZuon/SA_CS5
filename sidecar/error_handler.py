import logging
import time
import asyncio
from sidecar.token_rotator import mark_token_cooldown, get_valid_token, wait_until_next_available_token

MAX_RETRY = 3
RETRY_DELAY = 2  # giây

async def handle_github_error(resp, token, context=""):
    """
    Xử lý lỗi từ GitHub API response và xác định có phải lỗi nghiêm trọng không.
    """
    status = resp.status
    json_body = await resp.json()
    message = json_body.get("message", "No message provided")

    # Thông tin reset (nếu có)
    reset_ts = resp.headers.get("X-RateLimit-Reset")
    if reset_ts:
        reset_ts = int(reset_ts)
        now = int(time.time())
        remaining = reset_ts - now
        reset_info = f"⏳ Reset sau {remaining} giây"
    else:
        reset_ts = int(time.time()) + 60
        reset_info = "Không rõ thời gian reset"

    # Ghi log và xử lý theo mã lỗi
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

async def handle_github_error_with_retry(resp, token, context="", rollback_fn=None):
    """
    Gọi `handle_github_error`, nếu là lỗi nhẹ thì retry. Nếu nghiêm trọng, trả về True để dừng lại.

    Args:
        resp: response gốc từ aiohttp
        token: token hiện tại
        context: ngữ cảnh gọi API
        rollback_fn: callable async (nếu cần rollback database)

    Returns:
        True nếu nên abort, False nếu có thể tiếp tục
    """
    for attempt in range(MAX_RETRY):
        should_abort = await handle_github_error(resp, token, context)
        if should_abort:
            if rollback_fn:
                logging.info(f"↩️ Rollback do lỗi nghiêm trọng tại {context}")
                await rollback_fn()
            return True

        if attempt < MAX_RETRY - 1:
            logging.info(f"🔁 Retry lần {attempt + 1} sau {RETRY_DELAY} giây...")
            await asyncio.sleep(RETRY_DELAY)

    logging.warning(f"❌ Đã retry {MAX_RETRY} lần nhưng vẫn lỗi tại {context}")
    if rollback_fn:
        logging.info(f"↩️ Rollback do retry thất bại tại {context}")
        await rollback_fn()
    return True

async def safe_request(fetch_func, context="", max_retries=3):
    """
    Thực hiện một request GitHub có xử lý lỗi, xoay token, retry khi cần.

    Args:
        fetch_func: một hàm lambda nhận token và trả về coroutine request.
        context: mô tả ngữ cảnh để log
        max_retries: số lần retry tối đa

    Returns:
        Kết quả trả về từ fetch_func nếu thành công, hoặc raise Exception sau khi retry hết.
    """
    retries = 0
    while retries < max_retries:
        try:
            token = get_valid_token()
            result = await fetch_func(token)
            if result is not None:
                return result
        except Exception as e:
            logging.warning(f"⚠️ Request lỗi ({context}): {e}")
        retries += 1
        logging.info(f"🔁 Retry {retries}/{max_retries} ({context})")
        await asyncio.sleep(1)

        # Đợi nếu không còn token khả dụng
        if retries == max_retries:
            wait_time = wait_until_next_available_token()
            logging.warning(f"⏸ Đợi {wait_time:.1f}s do hết token khả dụng ({context})")
            await asyncio.sleep(wait_time)

    raise Exception(f"❌ Request thất bại sau {max_retries} lần ({context})")

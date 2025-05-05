import logging
import time
import asyncio
from main_app.token_rotator import mark_token_cooldown, get_valid_token, wait_until_next_available_token
from sidecar.metric_server import ERROR_COUNT
import re

MAX_RETRY = 5
RETRY_DELAY = 2  

async def handle_github_error(e, token, context=""):
    """
    Phân tích lỗi GitHub API từ message và quyết định có nên dừng hay tiếp tục khi bắt được ngoại lệ.
    Trả về True nếu lỗi nghiêm trọng và nên bỏ qua request.
    """
    # Lấy thông điệp từ ngoại lệ
    message = str(e)

    # Mặc định cooldown là 60 giây
    reset_ts = int(time.time()) + 60
    reset_info = "Không rõ thời gian reset"

    # Tìm timestamp từ message
    match = re.search(r"reset_ts=(\d+)", message)
    if match:
        reset_ts = int(match.group(1))
        remaining = reset_ts - int(time.time())
        reset_info = f"⏳ Reset sau {remaining} giây"
    else:
        reset_info = "Không rõ thời gian reset"

    ERROR_COUNT.inc()  # Tăng mỗi lần gặp lỗi

    # Kiểm tra thông điệp lỗi
    if "HTTP 403" in message:
        # Lỗi 403 Forbidden
        logging.warning(f"⚠️ 403 Forbidden tại {context}: {message}. Token {token[:8]}... cooldown. {reset_info}")
        mark_token_cooldown(token, reset_ts)
        return False  # Có thể retry
    elif "HTTP 401" in message:
        # Lỗi 401 Unauthorized
        logging.warning(f"❌ 401 Unauthorized tại {context}: Token {token[:8]}... không hợp lệ hoặc hết hạn.")
        mark_token_cooldown(token, int(time.time()) + 100)
        return True  # Có thể retry
    elif "HTTP 422" in message:
        # Lỗi 422 Unprocessable Entity
        logging.warning(f"⚠️ 422 Unprocessable Entity tại {context}: {message}")
        return True  # Lỗi nghiêm trọng, bỏ qua request
    elif "HTTP" in message and int(message.split('HTTP ')[1].split()[0]) >= 500:
        # Lỗi từ server (500-599)
        logging.warning(f"🔥 Lỗi server tại {context}: {message}")
        return False  # Có thể retry
    else:
        # Các lỗi khác
        logging.warning(f"⚠️ Lỗi tại {context}: {message}")
        return True  # Mặc định bỏ qua request

async def safe_request(fetch_func, context=""):
    retries = 0

    while retries < MAX_RETRY:
        token = None
        try:
            token = get_valid_token()
            logging.info(f"🔑 Sử dụng token {token[:10]}... cho request ({context})")
            result = await fetch_func(token)

            if isinstance(result, list):
                return result

        except Exception as e:
            retries += 1
            logging.warning(f"⚠️ Request lỗi ({context}): {e}")

            # Nếu lỗi xảy ra trước khi lấy token hợp lệ
            if token is None:
                if "Không còn token nào khả dụng" in str(e):
                    wait_time = max(wait_until_next_available_token(), 5)
                    logging.warning(f"⏸ Đợi {wait_time:.1f}s do hết token khả dụng ({context})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise e  # lỗi không phải do token

            # Có token → xử lý lỗi liên quan tới GitHub API
            should_skip = await handle_github_error(e, token, context)

            if should_skip:
                return None
            elif retries < MAX_RETRY:
                logging.info(f"🔁 Thử lại sau {RETRY_DELAY} giây... (Retry {retries}/{MAX_RETRY})")
                await asyncio.sleep(RETRY_DELAY)
            else:
                logging.warning(f"❌ Thử lại thất bại sau {MAX_RETRY} lần.")
                raise e

    # Nếu hết lượt retry
    raise Exception(f"❌ Request thất bại sau {MAX_RETRY} lần ({context})")

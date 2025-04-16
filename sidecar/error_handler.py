import logging
import time
from sidecar.token_rotator import mark_token_cooldown

async def handle_github_error(resp, token, context=""):
    """
    Xử lý lỗi từ GitHub API response.

    Args:
        resp: aiohttp.ClientResponse
        token: token đang dùng
        context: ngữ cảnh gọi API (ví dụ: owner/repo hay url)

    Trả về: bool - True nếu có lỗi nghiêm trọng, False nếu có thể bỏ qua
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
        reset_ts = int(time.time()) + 60  # default cooldown 60s nếu không có header
        reset_info = "Không rõ thời gian reset"

    if status == 403:
        logging.warning(f"⚠️ 403 Forbidden tại {context}: {message}. Token {token[:8]}... đang vào cooldown. {reset_info}")
        mark_token_cooldown(token, reset_ts)
        return True  # lỗi nghiêm trọng

    elif status == 401:
        logging.warning(f"❌ 401 Unauthorized tại {context}: Token {token[:8]}... có thể không hợp lệ.")
        mark_token_cooldown(token, reset_ts)
        return True

    elif status == 422:
        logging.warning(f"⚠️ 422 Unprocessable Entity tại {context}: {message}")
        return False  # có thể bỏ qua

    else:
        logging.warning(f"⚠️ Lỗi {status} tại {context}: {message}")
        return False

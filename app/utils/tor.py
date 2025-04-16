import aiohttp
from aiohttp_socks import ProxyConnector
import itertools
import os


# ===== 1. GitHub token list and round-robin rotation =====

TOKENS = [
  os.getenv("GITHUB_TOKEN_1"),
  os.getenv("GITHUB_TOKEN_2"),
  os.getenv("GITHUB_TOKEN_3")
]

# Create an infinite iterator to rotate through the tokens
token_cycle = itertools.cycle(TOKENS)

def get_next_token():
  """
  Return the next GitHub token in round-robin order.
  This avoids using the same token repeatedly and helps distribute API load.
  """
  return next(token_cycle)


# ===== 2. Create an aiohttp session using Tor proxy =====

async def create_tor_session():
  """
  Create an aiohttp.ClientSession that routes traffic through Tor SOCKS5 proxy.
  Make sure Tor is running on port 9050 (default).
  """
  connector = ProxyConnector.from_url('socks5://127.0.0.1:9050')
  session = aiohttp.ClientSession(connector=connector)
  return session
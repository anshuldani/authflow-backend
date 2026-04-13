"""
Shared slowapi limiter instance.
Import this in main.py and in any router that needs per-endpoint limits.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Key by client IP address
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


# Per-route rate limit decorators
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

PA_GENERATE_LIMIT = "10/minute"
APPEAL_LIMIT = "5/minute"
EXTRACT_LIMIT = "20/minute"

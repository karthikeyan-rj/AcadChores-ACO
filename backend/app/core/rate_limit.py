from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory rate limiter keyed by client IP.
# Shared across all route modules — import from here.
limiter = Limiter(key_func=get_remote_address)

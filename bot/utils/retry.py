import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# 3 попытки, задержка 0.5 → 4 сек (экспоненциальная)
http_retry = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
)
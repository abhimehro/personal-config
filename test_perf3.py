import time
import requests
import concurrent.futures
from typing import Any

HOROSCOPE_TIMEOUT = 5

HOROSCOPE_ENDPOINTS_TEMPLATE = [
    {
        "name": "horoscope-app-api.vercel.app",
        "url": "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily",
        "params_fn": lambda sign: {"sign": sign, "day": "today"},
    },
    {
        "name": "ohmanda.com",
        "url_fn": lambda sign: f"https://ohmanda.com/api/horoscope/{sign}",
        "params_fn": lambda _sign: {},
    },
]

def extract_horoscope_text(data: dict[str, Any]) -> str | None:
    if "data" in data and "horoscope_data" in data["data"]:
        return data["data"]["horoscope_data"]
    if "horoscope" in data:
        return data["horoscope"]
    return None

import logging
logger = logging.getLogger(__name__)

def fetch_horoscope(session: requests.Session, zodiac_sign: str) -> str:
    default_text = (
        "Trust your instincts and prioritize tasks that reduce future stress."
    )

    def fetch_endpoint(tmpl: dict[str, Any]) -> str | None:
        url = tmpl.get("url") or tmpl["url_fn"](zodiac_sign)
        params = tmpl["params_fn"](zodiac_sign)
        try:
            response = session.get(url, params=params, timeout=HOROSCOPE_TIMEOUT)
            response.raise_for_status()
            extracted = extract_horoscope_text(response.json())
            if extracted:
                return extracted
        except Exception as exc:
            pass
        return None

    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=min(len(HOROSCOPE_ENDPOINTS_TEMPLATE) or 1, 32)
    )

    futures = []

    try:
        for i, tmpl in enumerate(HOROSCOPE_ENDPOINTS_TEMPLATE):
            futures.append(executor.submit(fetch_endpoint, tmpl))

            # Wait a short time for the current endpoint before triggering the fallback.
            # Don't wait after the last endpoint is submitted.
            if i < len(HOROSCOPE_ENDPOINTS_TEMPLATE) - 1:
                try:
                    # Wait up to 1.5 seconds for the current request
                    done, _ = concurrent.futures.wait(futures, timeout=1.5, return_when=concurrent.futures.FIRST_COMPLETED)
                    # Check if any completed future resulted in a successful string
                    success_found = False
                    for future in done:
                        result = future.result()
                        if result:
                            success_found = True
                            return result

                    if success_found:
                        break
                except concurrent.futures.TimeoutError:
                    pass

        # If we exhausted all endpoints and wait thresholds without a successful return,
        # wait for any of the remaining pending requests to finish.
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                return result

    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return default_text


class SlowSession:
    def get(self, url, *args, **kwargs):
        class MockResp:
            def raise_for_status(self): pass
            def json(self):
                if "ohmanda" in url:
                    return {"horoscope": "Ohmanda says hi"}
                return {"data": {"horoscope_data": "Vercel says hi"}}

        if "vercel.app" in url:
            time.sleep(2.5)  # slow endpoint
            return MockResp()
        else:
            time.sleep(0.1)  # fast endpoint
            return MockResp()

if __name__ == "__main__":
    session = SlowSession()
    start = time.time()
    res = fetch_horoscope(session, "Aries")
    dur = time.time() - start
    print(f"Hedged: {dur:.4f}s, Res: {res}")

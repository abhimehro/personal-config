import re

with open("scripts/morning-brief/morning-brief.py", "r") as f:
    content = f.read()

# We need to simplify `fetch_horoscope` to avoid "Complex Method, Bumpy Road Ahead, Deep, Nested Complexity".
# The previous version had deeply nested `try/except` and loops.

old_func = """def fetch_horoscope(session: requests.Session, zodiac_sign: str) -> str:
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
            logger.warning("Horoscope failed from %s: %s", tmpl["name"], exc)
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

    return default_text"""

new_func = """def fetch_horoscope(session: requests.Session, zodiac_sign: str) -> str:
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
            logger.warning("Horoscope failed from %s: %s", tmpl["name"], exc)
        return None

    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=min(len(HOROSCOPE_ENDPOINTS_TEMPLATE) or 1, 32)
    )

    futures = []

    try:
        for i, tmpl in enumerate(HOROSCOPE_ENDPOINTS_TEMPLATE):
            futures.append(executor.submit(fetch_endpoint, tmpl))

            if i == len(HOROSCOPE_ENDPOINTS_TEMPLATE) - 1:
                continue

            done, _ = concurrent.futures.wait(
                futures, timeout=1.5, return_when=concurrent.futures.FIRST_COMPLETED
            )

            if any(future.result() for future in done if not future.exception()):
                break

        for future in concurrent.futures.as_completed(futures):
            result = future.exception() is None and future.result()
            if result:
                return result

    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return default_text"""

if old_func in content:
    content = content.replace(old_func, new_func)
    with open("scripts/morning-brief/morning-brief.py", "w") as f:
        f.write(content)
    print("Patched successfully.")
else:
    print("Could not find the function to patch.")

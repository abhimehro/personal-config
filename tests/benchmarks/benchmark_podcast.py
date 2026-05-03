import importlib
import os
import sys
import time

# Ensure the scripts directory is in sys.path
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scripts/morning-brief")),
)

morning_brief = importlib.import_module("morning-brief")


class _MockResponse:
    def raise_for_status(self):
        pass

    @property
    def content(self):
        return b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>America Adapts</title>
    <item>
      <title>Episode 1</title>
      <link>http://example.com/1</link>
      <published>Mon, 01 Jan 2024</published>
      <summary>Summary of episode 1 which is very interesting.</summary>
    </item>
    <item>
      <title>Episode 2</title>
      <link>http://example.com/2</link>
      <published>Tue, 02 Jan 2024</published>
      <summary>Summary of episode 2 about coastal science.</summary>
    </item>
    <item>
      <title>Episode 3</title>
      <link>http://example.com/3</link>
      <published>Wed, 03 Jan 2024</published>
      <summary>Summary of episode 3. Coastal science.</summary>
    </item>
  </channel>
</rss>
"""


class MockSession:
    """Minimal stand-in for `requests.Session` used by `fetch_podcast_section`.

    Implements both `get` (for the RSS fetch) and `post` (in case the real
    `PerplexityClient.chat` is exercised against this session in the future),
    so swapping in the production client doesn't silently break.
    """

    def get(self, url, timeout=None, **kwargs):
        return _MockResponse()

    def post(self, url, timeout=None, **kwargs):  # pragma: no cover - unused today
        return _MockResponse()


class BenchmarkPerplexityClient(morning_brief.PerplexityClient):
    """Real `PerplexityClient` with only `chat` stubbed.

    Subclassing the production client (instead of duplicating the
    `summarize_podcasts` join/split logic) ensures the benchmark exercises
    the real batching code path. If the production implementation diverges
    (e.g. delimiter changes), this benchmark catches it.
    """

    def __init__(self):
        super().__init__(api_key="mock_key")
        self.call_count = 0

    @property
    def enabled(self) -> bool:
        return True

    def chat(self, system_prompt, user_content, **kwargs):
        self.call_count += 1
        time.sleep(0.5)  # Simulate network latency
        if "---NEXT_PODCAST---" in user_content:
            parts = user_content.split("---NEXT_PODCAST---")
            return "===SEP===".join(
                "Mock summary for: " + p.replace("\n", " ")[:30] for p in parts
            )
        return "Mock summary for single item"


# Patch the session factory so `fetch_podcast_section` uses the mock.
morning_brief.build_retry_session = lambda *args, **kwargs: MockSession()


def main():
    llm = BenchmarkPerplexityClient()
    start = time.time()
    res = morning_brief.fetch_podcast_section(llm, limit=3)
    end = time.time()
    print(f"Time taken: {end - start:.4f}s")
    print(f"LLM API calls: {llm.call_count}")
    print(f"Result tags length: {len(res.tags)}")


if __name__ == "__main__":
    main()

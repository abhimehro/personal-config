import time
import sys
import os

# Ensure the scripts directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts/morning-brief')))

import importlib
morning_brief = importlib.import_module("morning-brief")

class MockPerplexityClient:
    def __init__(self, api_key: str = "mock_key"):
        self.api_key = api_key
        self.enabled = True
        self.call_count = 0

    def chat(self, system_prompt, user_content, **kwargs):
        self.call_count += 1
        time.sleep(0.5)  # Simulate network latency
        # If it's a batch request, it will have '---NEXT_PODCAST---'
        if '---NEXT_PODCAST---' in user_content:
            parts = user_content.split('---NEXT_PODCAST---')
            return "===SEP===".join("Mock summary for: " + p.replace('\n', ' ')[:30] for p in parts)
        return "Mock summary for single item"

    def summarize_podcast(self, text: str, session=None) -> str:
        return self.chat("...", text, max_tokens=100, temperature=0.5, session=session)

    def summarize_podcasts(self, texts: list[str], session=None) -> list[str]:
        if not texts:
            return []
        joined_texts = "\n\n---NEXT_PODCAST---\n\n".join(
            f"Podcast {i+1}:\n{t}" for i, t in enumerate(texts)
        )
        response = self.chat("...", joined_texts, max_tokens=100 * len(texts), temperature=0.5, session=session)
        if not response:
            return [""] * len(texts)
        summaries = [s.strip() for s in response.split("===SEP===")]
        while len(summaries) < len(texts):
            summaries.append("")
        return summaries[:len(texts)]

class MockSession:
    def get(self, url, timeout):
        class Response:
            def raise_for_status(self): pass
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
        return Response()

morning_brief.build_retry_session = lambda *args, **kwargs: MockSession()

def main():
    llm = MockPerplexityClient()
    start = time.time()
    res = morning_brief.fetch_podcast_section(llm, limit=3)
    end = time.time()
    print(f"Time taken: {end - start:.4f}s")
    print(f"LLM API calls: {llm.call_count}")
    print(f"Result tags length: {len(res.tags)}")

if __name__ == "__main__":
    main()

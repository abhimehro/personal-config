#!/Users/speedybee/Documents/dev/Scripts/raycast/venv/bin/python

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Generate Morning Brief
# @raycast.mode compact
# @raycast.needsConfirmation false

# Optional parameters:
# @raycast.icon ☕
# @raycast.packageName Daily Optimization

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests
import datetime
import feedparser
import concurrent.futures
import time

# --- CONFIGURATION ---
READWISE_TOKEN = "j7Rkp2B5TTOEAK0FN3yDeMFKrsrOjXMvH9mKC1ahYlG8it086R"

# Location: Baton Rouge
LAT = 30.4515
LON = -91.1871
ZODIAC_SIGN = "cancer" 

# Feed Dictionary: Name -> URL
FEEDS = {
    "🔍 The Lens": "https://thelensnola.org/feed/",
    "🏛️ LA Illuminator": "https://lailluminator.com/feed/",
    "🎙️ WRKF (NPR)": "https://www.wrkf.org/rss.xml",
    "⚖️ Verite News": "https://veritenews.org/feed/",
    "🌊 The Current": "https://thecurrentla.com/feed/"
}

# --- FUNCTIONS ---

def get_weather():
    """Fetches weather with auto-retries to handle VPN/DNS hiccups."""
    try:
        # Configuration for retry logic
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&current_weather=true&temperature_unit=fahrenheit&timezone=auto"
        
        # Increased timeout to 10s to give the VPN time to route
        response = session.get(url, timeout=10)
        data = response.json()
        
        current = data.get('current_weather', {})
        daily = data.get('daily', {})
        
        temp_now = current.get('temperature', 'N/A')
        high = daily.get('temperature_2m_max', ['N/A'])[0]
        rain_prob = daily.get('precipitation_probability_max', ['N/A'])[0]
        
        return f"""
        <h3>🌤️ Weather in Baton Rouge</h3>
        <ul>
            <li><strong>Current:</strong> {temp_now}°F</li>
            <li><strong>High Today:</strong> {high}°F</li>
            <li><strong>Rain Chance:</strong> {rain_prob}%</li>
        </ul>
        """
    except Exception as e:
        # Graceful fallback that won't ruin your reader formatting
        print(f"Weather Error: {e}") # Prints to log for debugging
        return f"""
        <h3>🌤️ Weather Unavailable</h3>
        <p><em>Could not connect to weather data. Check VPN connection.</em></p>
        """

def get_horoscope():
    """Fetches a quick daily horoscope."""
    try:
        url = f"https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily?sign={ZODIAC_SIGN}&day=today"
        response = requests.get(url, timeout=5)
        data = response.json()
        horoscope_text = data.get('data', {}).get('horoscope_data', "No text found.")
        
        return f"""
        <h3>🦀 Daily Horoscope ({ZODIAC_SIGN.capitalize()})</h3>
        <p>{horoscope_text}</p>
        """
    except Exception as e:
        return f"<p>Could not fetch horoscope: {e}</p>"

def fetch_single_feed(name, url, limit=3):
    """Helper function to fetch a single RSS feed."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        feed = feedparser.parse(response.content)
        
        if not feed.entries:
            return ""

        items_html = []
        for entry in feed.entries[:limit]:
            title = entry.get('title', 'No Title')
            link = entry.get('link', '#')
            summary_raw = entry.get('summary', entry.get('description', ''))
            summary = summary_raw.replace('<p>', '').replace('</p>', '')
            summary = summary[:150] + "..." if len(summary) > 150 else summary
            
            item = f"""
            <li style="margin-bottom: 8px;">
                <a href="{link}" style="text-decoration: none; font-weight: bold; color: #2c3e50;">{title}</a><br>
                <span style="color: #666; font-size: 0.9em;">{summary}</span>
            </li>
            """
            items_html.append(item)
            
        return f"""
        <h3>{name}</h3>
        <ul>
            {''.join(items_html)}
        </ul>
        """
    except Exception:
        return "" # Fail silently for individual feeds to keep the brief clean

def get_all_rss_parallel(feeds_dict):
    """Fetches all RSS feeds in parallel using ThreadPoolExecutor."""
    results = []
    
    # We use a ThreadPoolExecutor to run the network requests simultaneously
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit all tasks
        future_to_feed = {executor.submit(fetch_single_feed, name, url): name for name, url in feeds_dict.items()}
        
        # Gather results as they complete
        for future in concurrent.futures.as_completed(future_to_feed):
            data = future.result()
            if data:
                results.append(data)
                
    return "".join(results)

def save_to_reader(html_content):
    """Pushes the compiled HTML to Readwise Reader."""
    url = "https://readwise.io/api/v3/save"
    headers = {"Authorization": f"Token {READWISE_TOKEN}"}
    
    today_str = datetime.date.today().strftime("%B %d, %Y")
    unique_id = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    
    payload = {
        "url": f"https://internal-brief.local/daily-{unique_id}", 
        "html": html_content,
        "title": f"Morning Brief: {today_str}",
        "author": "Raycast Assistant",
        "tags": ["morning-routine", "dashboard"],
        "should_clean_html": False 
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    
    if response.status_code in [200, 201]:
        print("✅ Brief sent to Reader")
    else:
        print(f"❌ Error sending to Reader: {response.text}")

# --- MAIN EXECUTION ---

def main():
    print("⏳ Gathering local intel...")
    
    # 1. Gather Data (Parallel execution for feeds)
    # We run weather/horoscope first (fast), then the heavy RSS lifting
    weather_html = get_weather()
    horoscope_html = get_horoscope()
    
    # Fetch news
    news_html = get_all_rss_parallel(FEEDS)

    # 2. Build Document
    full_content = f"""
    <h1>Morning Briefing</h1>
    <p><em>{datetime.date.today().strftime("%A, %B %d")}</em></p>
    <hr>
    {weather_html}
    <hr>
    {news_html}
    <hr>
    {horoscope_html}
    <hr>
    <p>🚀 <strong>Focus:</strong> Check GitHub PRs and Fieldwork Schedule.</p>
    """
    
    # 3. Deliver
    save_to_reader(full_content)

if __name__ == "__main__":
    main()

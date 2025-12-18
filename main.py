import feedparser
import requests
import google.generativeai as genai
import os
from datetime import datetime
import pytz

# --- CONFIGURATION (Secrets loaded from GitHub) ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# --- 1. GET WEATHER (Salé) ---
def get_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=34.05&longitude=-6.82&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
    try:
        data = requests.get(url).json()['daily']
        today_summary = f"Today: Max {data['temperature_2m_max'][0]}°C, Min {data['temperature_2m_min'][0]}°C. Rain: {data['precipitation_probability_max'][0]}%"
        tomorrow_summary = f"Tomorrow: Max {data['temperature_2m_max'][1]}°C, Min {data['temperature_2m_min'][1]}°C"
        return f"🌤️ WEATHER (Salé):\n{today_summary}\n{tomorrow_summary}"
    except Exception as e:
        return f"Weather Error: {e}"

# --- 2. GET NEWS & SPORTS ---
def get_feeds():
    sources = [
        ("BBC Arabic", "https://feeds.bbci.co.uk/arabic/rss.xml"),
        ("Sky News", "https://www.skynewsarabia.com/web/rss"),
        ("Hespress", "https://www.hespress.com/feed"),
        ("Asharq", "https://aawsat.com/feed"),
        ("Sports (Wydad/Real)", "https://news.google.com/rss/search?q=Real+Madrid+OR+Wydad+Casablanca+OR+Equipe+Maroc+Football&hl=ar&gl=MA&ceid=MA:ar")
    ]
    
    raw_text = ""
    for name, url in sources:
        try:
            feed = feedparser.parse(url)
            # Take top 4 stories from each source
            for entry in feed.entries[:4]:
                title = entry.title
                summary = entry.get('summary', entry.get('description', ''))
                # Clean HTML tags slightly
                summary = summary.replace('<br>', ' ').replace('<p>', '')[:200]
                raw_text += f"SOURCE: {name}\nTITLE: {title}\nSUMMARY: {summary}\n\n"
        except Exception as e:
            print(f"Failed to read {name}: {e}")
            
    return raw_text

# --- 3. AI PROCESSING (Gemini) ---
def generate_brief(weather_data, news_data):
    model = genai.GenerativeModel('gemini-pro')
    
    system_prompt = """
    You are a Personal Intelligence Assistant. Create a Morning Brief in Arabic.
    
    Structure:
    1. 🌤️ <b>Weather (Salé)</b>: Summarize the provided weather data.
    2. ⚽ <b>Sports</b>: Focus on Wydad AC, Real Madrid, Morocco Team. If no news, say "No major updates".
    3. 🌍 <b>Top News</b>: Pick top 5 stories (Politics/Biz). Deduplicate.
    
    Format Rules:
    - Use HTML tags: <b>, <i>, <a>. 
    - NO <br>, NO <div>, NO Markdown (*).
    - Emoji headers.
    """
    
    user_message = f"Weather Data:\n{weather_data}\n\nNews Data:\n{news_data}"
    
    try:
        response = model.generate_content(f"{system_prompt}\n\n{user_message}")
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

# --- 4. SEND TO TELEGRAM ---
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("Fetching data...")
    weather = get_weather()
    news = get_feeds()
    
    print("Thinking...")
    brief = generate_brief(weather, news)
    
    print("Sending...")
    send_telegram(brief)
    print("Done!")

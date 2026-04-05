import httpx
import feedparser
from datetime import datetime
from urllib.parse import quote

import config
from database import SessionLocal
from models import UserPreferences, ClassSchedule

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# WMO weather interpretation codes → human-readable descriptions
WMO_CODES: dict[int, str] = {
    0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing Rime Fog",
    51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Dense Drizzle",
    61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
    71: "Slight Snowfall", 73: "Moderate Snowfall", 75: "Heavy Snowfall",
    77: "Snow Grains", 80: "Slight Rain Showers", 81: "Moderate Rain Showers",
    82: "Violent Rain Showers", 85: "Slight Snow Showers", 86: "Heavy Snow Showers",
    95: "Thunderstorm", 96: "Thunderstorm with Slight Hail",
    99: "Thunderstorm with Heavy Hail",
}


class BriefingEngine:
    """Fetches weather, news, and schedule then sends a Telegram briefing.

    Weather  → Open-Meteo API (free, no key)
    News     → Google News RSS via feedparser (free, no key)
    Telegram → Telegram Bot API (free, just needs a BotFather token)
    """

    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
    NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    def __init__(self) -> None:
        pass

    @property
    def telegram_url(self) -> str:
        token = config.TELEGRAM_BOT_TOKEN
        if token and token != "your_telegram_bot_token":
            return f"https://api.telegram.org/bot{token}/sendMessage"
        return ""

    # ── External data fetchers ─────────────────────────────────────────

    async def fetch_weather(self, city: str) -> dict:
        """Use Open-Meteo (free, no API key) to get current weather."""
        async with httpx.AsyncClient(timeout=15) as client:
            # Step 1: geocode city name → lat/lon
            geo_resp = await client.get(
                self.GEOCODE_URL, params={"name": city, "count": 1}
            )
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()
            results = geo_data.get("results")
            if not results:
                raise ValueError(f"City '{city}' not found by geocoder")
            place = results[0]
            lat, lon = place["latitude"], place["longitude"]
            resolved_name = place.get("name", city)

            # Step 2: fetch current weather
            weather_resp = await client.get(
                self.WEATHER_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": "true",
                    "hourly": "relative_humidity_2m",
                    "forecast_days": 1,
                },
            )
            weather_resp.raise_for_status()
            w = weather_resp.json()

        current = w["current_weather"]
        # Grab first hourly humidity value as representative
        humidity_list = w.get("hourly", {}).get("relative_humidity_2m", [])
        humidity = humidity_list[0] if humidity_list else None

        wmo_code = current.get("weathercode", 0)
        description = WMO_CODES.get(wmo_code, f"Code {wmo_code}")

        return {
            "city": resolved_name,
            "temp": current["temperature"],
            "feels_like": current["temperature"],  # Open-Meteo doesn't provide feels-like in free tier
            "description": description,
            "humidity": humidity,
            "wind_speed": current["windspeed"],
        }

    async def fetch_news(self, topics: str, count: int = 3) -> list[dict]:
        """Parse Google News RSS feed (free, no API key)."""
        url = self.NEWS_RSS.format(query=quote(topics))
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        articles: list[dict] = []
        for entry in feed.entries[:count]:
            # Google News titles sometimes include " - Source" at the end
            title = entry.get("title", "No title")
            source = "Google News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0]
                source = parts[1]
            articles.append({
                "title": title,
                "source": source,
                "url": entry.get("link", ""),
            })
        return articles

    def fetch_schedule(self, day: str | None = None) -> list[dict]:
        if day is None:
            day = DAYS[datetime.now().weekday()]
        db = SessionLocal()
        try:
            rows = (
                db.query(ClassSchedule)
                .filter(ClassSchedule.day_of_week == day)
                .order_by(ClassSchedule.time)
                .all()
            )
            return [
                {
                    "time": r.time,
                    "subject": r.subject,
                    "location": r.location,
                }
                for r in rows
            ]
        finally:
            db.close()

    # ── Message builder ────────────────────────────────────────────────

    def build_message(
        self,
        weather: dict | None,
        news: list[dict],
        schedule: list[dict],
    ) -> str:
        now = datetime.now()
        day_name = DAYS[now.weekday()]
        lines: list[str] = []
        lines.append(f"*Daily Briefing — {day_name}, {now.strftime('%B %d, %Y')}*")
        lines.append("")

        # Weather section
        if weather:
            lines.append("*Weather*")
            lines.append(f"City: {weather['city']}")
            lines.append(f"Temp: {weather['temp']} C")
            if weather.get("humidity") is not None:
                lines.append(f"Humidity: {weather['humidity']}%")
            lines.append(f"Wind: {weather['wind_speed']} km/h")
            lines.append(f"Conditions: {weather['description']}")
        else:
            lines.append("*Weather* — _unavailable_")
        lines.append("")

        # News section
        lines.append("*Top Headlines*")
        if news:
            for i, article in enumerate(news, 1):
                lines.append(f"{i}. {article['title']} ({article['source']})")
        else:
            lines.append("_No headlines found._")
        lines.append("")

        # Schedule section
        lines.append(f"*Today's Classes ({day_name})*")
        if schedule:
            for entry in schedule:
                loc = f" — {entry['location']}" if entry["location"] else ""
                lines.append(f"- {entry['time']}  {entry['subject']}{loc}")
        else:
            lines.append("_No classes scheduled for today._")

        lines.append("")
        lines.append("_Have a productive day!_")
        return "\n".join(lines)

    # ── Telegram sender ────────────────────────────────────────────────

    async def send_telegram(self, chat_id: str, text: str) -> dict:
        if not self.telegram_url:
            return {"ok": False, "description": "Telegram bot token not configured"}
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(self.telegram_url, json=payload)
            resp.raise_for_status()
            return resp.json()

    # ── Orchestrator (called by scheduler & manual trigger) ────────────

    async def run(self, preview_only: bool = False) -> dict:
        db = SessionLocal()
        try:
            prefs = db.query(UserPreferences).first()
            if not prefs:
                return {"ok": False, "detail": "No user preferences configured."}
        finally:
            db.close()

        city = prefs.city
        topics = prefs.news_topics
        chat_id = prefs.telegram_chat_id

        # Fetch data (gracefully handle individual failures)
        weather = None
        news: list[dict] = []
        schedule: list[dict] = []

        try:
            weather = await self.fetch_weather(city)
        except Exception as exc:
            print(f"[BriefingEngine] Weather fetch failed: {exc}")

        try:
            news = await self.fetch_news(topics)
        except Exception as exc:
            print(f"[BriefingEngine] News fetch failed: {exc}")

        schedule = self.fetch_schedule()

        message = self.build_message(weather, news, schedule)

        result_data = {
            "ok": True,
            "message": message,
            "weather": weather,
            "news": news,
            "schedule": schedule,
            "day": DAYS[datetime.now().weekday()],
            "date": datetime.now().strftime("%B %d, %Y"),
        }

        # Preview mode: return message without sending to Telegram
        if preview_only:
            return {**result_data, "sent": False}

        if not chat_id:
            return {**result_data, "sent": False, "detail": "Telegram Chat ID not configured in preferences."}

        if not self.telegram_url:
            return {**result_data, "sent": False, "detail": "Telegram bot token not set. Add TELEGRAM_BOT_TOKEN to .env and restart the server."}

        try:
            tg_result = await self.send_telegram(chat_id, message)
            return {**result_data, "sent": True, "telegram_response": tg_result}
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            return {**result_data, "sent": False, "detail": f"Telegram API error ({exc.response.status_code}): {body}"}
        except Exception as exc:
            return {**result_data, "sent": False, "detail": f"Telegram send failed: {exc}"}

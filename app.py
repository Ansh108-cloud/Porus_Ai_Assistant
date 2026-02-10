import streamlit as st
import wikipedia
import requests
import datetime
import os
from bs4 import BeautifulSoup

# ================= CONFIG =================
st.set_page_config(
    page_title="Porus AI Cloud",
    layout="wide"
)

WEATHER_API_KEY = "a81cd6f2d72b04886cfe9461dac80c2a"

# ================= SESSION =================
if "messages" not in st.session_state:
    st.session_state.messages = []

# ================= CORE FUNCTIONS =================

def get_weather(cmd):
    city = cmd.replace("weather", "").replace("in", "").strip()
    if not city:
        return "Please tell me a city name."

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    res = requests.get(url).json()

    if res.get("cod") != 200:
        return "City not found."

    return (
        f"🌤 Weather in {city.title()}\n\n"
        f"Condition: {res['weather'][0]['description'].title()}\n"
        f"Temperature: {res['main']['temp']}°C\n"
        f"Humidity: {res['main']['humidity']}%\n"
        f"Wind: {res['wind']['speed']} m/s"
    )

def get_news():
    try:
        res = requests.get("https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en")
        soup = BeautifulSoup(res.content, "xml")
        item = soup.find("item")
        return "📰 " + item.title.text
    except:
        return "Failed to fetch news."

def process_command(cmd):
    cmd = cmd.lower()

    if "weather" in cmd:
        return get_weather(cmd)

    elif "news" in cmd:
        return get_news()

    elif "who is" in cmd or "wikipedia" in cmd:
        try:
            query = cmd.replace("who is", "").replace("wikipedia", "").strip()
            return wikipedia.summary(query, sentences=2)
        except:
            return "No information found."

    elif "time" in cmd:
        return f"⏰ Current time: {datetime.datetime.now().strftime('%H:%M:%S')}"

    else:
        return "🤖 Cloud mode active. Voice, image generation & automation are available only in Local Mode."

# ================= UI =================

st.markdown("""
<style>
.stApp { background-color: #0f0f0f; color: white; }
.chat { padding: 12px; border-radius: 10px; margin-bottom: 10px; }
.user { background: #1f6feb; }
.bot { background: #21262d; }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Porus AI – Cloud Edition")
st.caption("Lightweight AI running on Streamlit Cloud")

for msg in st.session_state.messages:
    role = "user" if msg["role"] == "user" else "assistant"
    color = "user" if role == "user" else "bot"
    st.markdown(f"<div class='chat {color}'>{msg['content']}</div>", unsafe_allow_html=True)

prompt = st.chat_input("Ask Porus AI (Cloud Mode)...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    response = process_command(prompt)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

st.sidebar.markdown("### ⚠️ Cloud Limitations")
st.sidebar.info(
    "Voice, Image Generation, Camera, Automation\n"
    "are disabled on Streamlit Cloud.\n\n"
    "Run Local Mode for full features."
)

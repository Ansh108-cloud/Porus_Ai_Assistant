import streamlit as st
import wikipedia
import requests
import datetime
from bs4 import BeautifulSoup
from groq import Groq

# ================= CONFIG =================
st.set_page_config(page_title="Porus AI – Cloud", layout="wide")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
WEATHER_API_KEY = "a81cd6f2d72b04886cfe9461dac80c2a"

# ================= SESSION =================
if "messages" not in st.session_state:
    st.session_state.messages = []

# ================= AI CHAT =================
def ai_chat(prompt):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are Porus AI, a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=5000,
        temperature=0.7
    )
    return response.choices[0].message.content

# ================= COMMANDS =================
def get_weather(cmd):
    city = cmd.replace("weather", "").replace("in", "").strip()
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    res = requests.get(url).json()
    if res.get("cod") != 200:
        return "City not found."
    return f"🌤 {city.title()}: {res['main']['temp']}°C, {res['weather'][0]['description']}"

def get_news():
    res = requests.get("https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en")
    soup = BeautifulSoup(res.content, "xml")
    return "📰 " + soup.find("item").title.text

def process_input(text):
    t = text.lower()
    if "weather" in t:
        return get_weather(t)
    if "news" in t:
        return get_news()
    if "who is" in t or "wikipedia" in t:
        try:
            return wikipedia.summary(text, sentences=2)
        except:
            return "No information found."
    return ai_chat(text)

# ================= UI =================
st.title("🤖 Porus AI – Cloud Edition")
st.caption("Real Chat AI powered by Groq")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("Ask Porus AI...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("assistant"):
        reply = process_input(prompt)
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

st.sidebar.info("⚠️ Voice, Image, Camera & Automation are Local-only features.")

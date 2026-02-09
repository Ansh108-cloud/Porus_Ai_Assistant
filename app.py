import streamlit as st
import datetime
import wikipedia
import pywhatkit
import webbrowser
import time
import os
import subprocess
import requests
import speech_recognition as sr
import streamlit.components.v1 as components
import pyautogui
import psutil
import shutil
import cv2
import torch
from diffusers import StableDiffusionPipeline
import warnings
import base64
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# ================= CRITICAL FIXES =================
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ================= CONFIG =================
# Using 127.0.0.1 is more stable for local requests than 'localhost'
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "llama3:latest" 
VISION_MODEL = "llama3.2-vision:latest" 
TODO_FILE = "porus_todo.txt"

# --- CREDENTIALS ---
SENDER_EMAIL = "hodarabhay553@gmail.com" 
SENDER_PASS = "azft kdeh xxvq hgdp" 
WEATHER_API_KEY = "a81cd6f2d72b04886cfe9461dac80c2a"

st.set_page_config(page_title="Porus AI Pro", layout="wide")

@st.cache_resource
def load_sd_pipe():
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float32,
        safety_checker=None
    )
    pipe = pipe.to("cpu")   # change to "cuda" later if GPU
    pipe.enable_attention_slicing()
    return pipe

sd_pipe = load_sd_pipe()

# ================= CORE FUNCTIONS =================

def warmup_ollama():
    """Forces Ollama to load the model from Disk to RAM/GPU."""
    try:
        # 180s timeout ensures large models load even on slower HDDs
        # keep_alive: -1 keeps model in RAM for your entire presentation
        requests.post(
            OLLAMA_URL, 
            json={"model": MODEL_NAME, "prompt": "", "keep_alive": -1}, 
            timeout=180
        )
        return True
    except Exception as e:
        st.error(f"Initialization Warning: {e}")
        return False

def speak(text):
    clean_text = text.replace('"', "'").replace("\n", " ")
    voice = st.session_state.voice_gender
    js_code = f"""
    <script>
    var msg = new SpeechSynthesisUtterance("{clean_text}");
    var voices = window.speechSynthesis.getVoices();
    for(var i=0;i<voices.length;i++) {{
        if(voices[i].name.toLowerCase().includes('{voice}')) {{
            msg.voice = voices[i]; break;
        }}
    }}
    window.speechSynthesis.speak(msg);
    </script>
    """
    components.html(js_code, height=0)

# --- IMAGE TOOLS ---
def generate_ai_image(prompt):
    with torch.no_grad():
        image = sd_pipe(
            prompt,
            num_inference_steps=25,
            guidance_scale=7.5
        ).images[0]

    # optional disk save (for history)
    os.makedirs("generated_images", exist_ok=True)
    save_path = f"generated_images/porus_{int(time.time())}.png"
    image.save(save_path)

    return image, save_path

def analyze_uploaded_image(uploaded_file, user_query):
    try:
        image_bytes = uploaded_file.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        payload = {
            "model": VISION_MODEL,
            "messages": [{"role": "user", "content": user_query, "images": [image_base64]}],
            "stream": False,
            "keep_alive": -1
        }
        # Increased timeout for vision tasks
        resp = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=300)
        return resp.json().get("message", {}).get("content", "Analysis failed.")
    except Exception as e:
        return f"Vision Error: {str(e)}. Ensure {VISION_MODEL} is pulled."

# --- SYSTEM AUTOMATION FUNCTIONS ---
def manage_todo(cmd):
    if "add" in cmd:
        task = cmd.replace("add", "").replace("to my todo list", "").replace("to todo", "").strip()
        with open(TODO_FILE, "a") as f: f.write(task + "\n")
        return f"Task added: {task}"
    elif any(x in cmd for x in ["show", "what", "read"]):
        if os.path.exists(TODO_FILE):
            with open(TODO_FILE, "r") as f: tasks = f.readlines()
            return "Your tasks: " + ", ".join([t.strip() for t in tasks]) if tasks else "Empty list."
        return "No todo list found."
    elif any(x in cmd for x in ["clear", "delete"]):
        if os.path.exists(TODO_FILE): os.remove(TODO_FILE); return "Todo list cleared."
        return "Already empty."

def take_screenshot():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{ts}.png"
    ss = pyautogui.screenshot()
    ss.save(filename)
    return filename

def get_system_stats():
    cpu, ram = psutil.cpu_percent(), psutil.virtual_memory().percent
    battery = psutil.sensors_battery()
    percent = battery.percent if battery else "Unknown"
    # Logic for a color-coded RAM warning in UI
    status = "🔴 CRITICAL" if ram > 80 else "🟢 HEALTHY"
    return f"System: CPU {cpu}%, RAM {ram}% ({status}), Battery {percent}%."

def organize_desktop():
    user_home = os.path.expanduser("~")
    paths = [os.path.join(user_home, "OneDrive", "Desktop"), os.path.join(user_home, "Desktop")]
    desktop = next((p for p in paths if os.path.exists(p)), None)
    if not desktop: return "Desktop not found."
    folders = {"Images": [".jpg", ".png", ".jpeg", ".gif"], "Docs": [".pdf", ".txt", ".docx"], "Setups": [".exe", ".msi"]}
    moved = 0
    for file in os.listdir(desktop):
        file_path = os.path.join(desktop, file)
        if os.path.isdir(file_path): continue
        ext = os.path.splitext(file)[1].lower()
        for folder, exts in folders.items():
            if ext in exts:
                target = os.path.join(desktop, folder)
                os.makedirs(target, exist_ok=True)
                shutil.move(file_path, os.path.join(target, file))
                moved += 1
    return f"Organized {moved} files."

def get_weather(cmd):
    # Extract city from command
    city = cmd.replace("weather in", "").replace("weather for", "").replace("weather", "").strip()
    if not city:
        return "Please specify a city to get the weather."

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url)
        data = res.json()

        if data.get("cod") != 200:
            return f"Could not get weather for '{city}'. Check city name."

        weather = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        wind = data["wind"]["speed"]

        return (
            f"Weather in {city}:\n"
            f"Condition: {weather}\n"
            f"Temperature: {temp}°C (Feels like {feels_like}°C)\n"
            f"Humidity: {humidity}%\n"
            f"Wind speed: {wind} m/s"
        )
    except Exception as e:
        return f"Weather fetch error: {str(e)}"

def intruder_alert_mode():
    speak("Entering Guard Mode.")
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        if len(faces) > 0:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            cv2.imwrite(f"intruder_{ts}.png", frame)
            cap.release(); return f"ALERT! Face detected. Saved as intruder_{ts}.png"
        cap.release(); return "Area is secure."
    return "Camera Error."

# ================= SESSION STATE =================
if "messages" not in st.session_state: st.session_state.messages = []
if "voice_gender" not in st.session_state: st.session_state.voice_gender = "male"
if "warmed_up" not in st.session_state: st.session_state.warmed_up = False
if "current_mode" not in st.session_state: st.session_state.current_mode = "Chat Mode"
if "last_image" not in st.session_state: st.session_state.last_image = None
if "last_image_path" not in st.session_state: st.session_state.last_image_path = None


# ================= COMMAND HANDLER =================

def execute_command(command, uploaded_file=None):
    cmd = command.lower()
    mode = st.session_state.current_mode

    if mode == "Image Generator":
        if uploaded_file and any(x in cmd for x in ["what", "describe", "summarize", "analyze"]):
            return analyze_uploaded_image(uploaded_file, command)
        else:
            image, path = generate_ai_image(command)
            st.session_state.last_image = image      # PIL IMAGE
            st.session_state.last_image_path = path  # FILE PATH
            return f"I have generated the image for: {command}"


    elif mode == "Command Mode":
        if "todo" in cmd: return manage_todo(cmd)

        # --- NEW SEARCH FEATURE ---
        elif "search" in cmd or "google" in cmd:
            query = cmd.replace("search", "").replace("google", "").replace("for", "").strip()
            if query:
                url = f"https://www.google.com/search?q={query}"
                webbrowser.open(url)
                return f"Opening Google search results for: {query}"
            return "What would you like me to search for?"

        elif "open cmd" in cmd or "open command prompt" in cmd:
            subprocess.Popen("start cmd", shell=True)
            return "Opening Command Prompt."

        elif "open camera" in cmd:
            os.system("start microsoft.windows.camera:")
            return "Opening Camera App."


        # --- NEW WEBSITE OPENER ---
        elif "open" in cmd:
            site = cmd.replace("open", "").strip()
            url = f"https://www.{site}.com" if "." not in site else f"https://{site}"
            webbrowser.open(url)
            return f"Opening {site}..."
        
        elif "screenshot" in cmd:
            path = take_screenshot()
            st.image(path)
            return f"Screenshot taken and saved as {path}."
        elif "who is" in cmd or "wikipedia" in cmd:
            try: return wikipedia.summary(cmd.replace("who is",""), sentences=2)
            except: return "No info found."
        elif "play" in cmd:
            pywhatkit.playonyt(cmd.replace("play","")); return "Playing on YouTube."
        elif any(x in cmd for x in ["system", "cpu", "ram", "battery"]): return get_system_stats()
        elif "guard" in cmd or "intruder" in cmd: return intruder_alert_mode()
        elif "clean" in cmd: return organize_desktop()
        
        elif "weather" in cmd:
         return get_weather(cmd)

        elif "news" in cmd:
            try:
                res = requests.get("https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en")
                soup = BeautifulSoup(res.content, features="xml")
                first_item = soup.find('item')
                if  first_item and first_item.title:
                    return "Top News: " + first_item.title.text
                else:
                    return "Could not fetch news."
            except Exception as e:
                return f"News fetch error: {str(e)}"

        return "Command Mode active. Ask for system stats, music, or files."

    else:
        # SYNCED CHAT LOGIC FOR HIGH RAM USAGE
        try:
            payload = {
                "model": MODEL_NAME, 
                "prompt": command, 
                "stream": False, 
                "keep_alive": -1,
                "options": {
                    "num_predict": 1024,  # Increased from 128 to 1024 for long responses
                    "num_ctx": 4096,     # Increased context so it remembers more of the chat
                    "temperature": 0.7,  # Higher temperature makes it more creative/wordy
                    "top_p": 0.9,
                }
            }
            # Increased timeout to 300s to stop the 180s/120s crash
            resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
            if resp.status_code == 200:
                return resp.json().get("response", "I'm thinking...")
            else:
                return f"Ollama Server Error: {resp.status_code}. Check 'ollama list'."
        except Exception as e: 
            return f"Porus is disconnected: {str(e)}. Please ensure 'ollama serve' is running."

# ================= MODERN UI =================

st.markdown("""
<style>
    .stApp { background-color: #0f0f0f; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #333; }
    .circle { width: 400px; height: 400px; margin: 0 auto; background: radial-gradient(circle, #00f2ff, #0066ff); border-radius: 50%; box-shadow: 0 0 30px #00f2ff; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
    .header-text { text-align: center; font-size: 28px; font-weight: bold; color: #00f2ff; margin-bottom: 20px;}
    .health-card { padding: 10px; background: #262626; border-radius: 8px; margin-bottom: 5px; border-left: 5px solid #00f2ff; }
    .todo-item { padding: 5px; background: #1a1a1a; border-radius: 4px; margin-bottom: 3px; border-bottom: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

if not st.session_state.warmed_up:
    with st.spinner("🚀 Initializing Porus AI (Loading to RAM)..."):
        if warmup_ollama(): 
            st.session_state.warmed_up = True
            st.success("AI Online and Loaded!")

with st.sidebar:
    st.markdown("### 🤖 Porus Control Center")
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=60)
    st.session_state.current_mode = st.selectbox("🎯 Select AI Mode", ["Chat Mode", "Command Mode", "Image Generator"])
    
    st.divider()
    st.markdown("#### 📂 Vision Upload")
    uploaded_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
    
    st.divider()
    st.markdown("#### 📅 To-Do List")
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE, "r") as f:
            for t in f.readlines(): st.markdown(f"<div class='todo-item'>📌 {t.strip()}</div>", unsafe_allow_html=True)
    
    st.divider()
    st.markdown("#### 🌡️ System Health")
    st.markdown(f"<div class='health-card'>{get_system_stats()}</div>", unsafe_allow_html=True)

    # st.session_state.voice_gender = st.radio("🗣️ Voice", ["Male", "Female"]).lower()
    
    st.divider()
    if st.button("📸 Take Screenshot"): st.image(take_screenshot())
    if st.button("🧹 Clean Desktop"): st.toast(organize_desktop())
    if st.button("🛡️ Guard Mode"): st.warning(intruder_alert_mode())
    if st.button("🗑️ Reset Chat"): 
        st.session_state.messages = []
        st.rerun()

st.markdown('<div class="circle"></div>', unsafe_allow_html=True)
st.markdown(f'<div class="header-text">PORUS PRO: {st.session_state.current_mode.upper()}</div>', unsafe_allow_html=True)

if st.session_state.last_image:
    st.image(
        st.session_state.last_image,
        caption="🎨 Porus AI Generated Image",
        use_container_width=True
    )

    st.download_button(
        "⬇️ Download Image",
        data=open(st.session_state.last_image_path, "rb"),
        file_name=os.path.basename(st.session_state.last_image_path),
        mime="image/png"
    )

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input(f"Type here ({st.session_state.current_mode})..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Porus is processing..."):
            response = execute_command(prompt, uploaded_file)
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        speak(response)

if st.button("🎙️ Voice Command"):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source)
        st.toast("Listening...")
        try:
            audio = r.listen(source, timeout=5)
            text = r.recognize_google(audio)
            st.session_state.messages.append({"role": "user", "content": text})
            st.rerun()
        except Exception as e: 
            st.error(f"Mic error: {e}")
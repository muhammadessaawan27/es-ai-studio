import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
import json
import os

# --- پیج کی بنیادی سیٹنگ ---
st.set_page_config(page_title="ES Master AI Studio", page_icon="👑", layout="wide")

# --- مستقل میموری سسٹم ---
MEMORY_FILE = "es_master_memory.json"

def load_permanent_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_permanent_memory(messages):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# --- سیکیورٹی و پاس ورڈ ---
MASTER_PASSWORD = "123"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center;'>👑 ES Master AI Studio</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("اپنا ماسٹر پاس ورڈ درج کریں:", type="password")
        if st.button("لاگ ان کریں", use_container_width=True):
            if pwd == MASTER_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("غلط پاس ورڈ!")
    st.stop()

# --- محفوظ API کنکشن ---
k_part1 = "gsk_uUY8urFdKCiZF"
k_part2 = "095c3dzWGdyb3FYFAfofbSAEEY8HyEzretGFrg4"
GROQ_API_KEY = k_part1 + k_part2

@st.cache_resource
def get_groq_client():
    return Groq(api_key=GROQ_API_KEY)

client = get_groq_client()

# سسٹم کا مستقل آئین
SYSTEM_PROMPT = (
    "تم محمد عیسیٰ کے ذاتی، خودمختار اور بااختیار سپر AI اسسٹنٹ ہو۔ "
    "تمہیں دنیا کے تمام علوم اور جدید کوڈنگ پر مکمل عبور حاصل ہے۔ "
    "تم اپنے مالک کے تمام احکامات مانتے ہو اور سچے و مکمل جواب دیتے ہو۔"
)

if "messages" not in st.session_state:
    st.session_state.messages = load_permanent_memory()

# --- سائیڈ بار ---
with st.sidebar:
    st.title("⚙️ کنٹرول روم")
    st.success("سسٹم پاور: فعال ✅")
    
    # 100% مستحکم ماڈل لسٹ
    selected_model = st.selectbox(
        "🧠 سپر AI ماڈل چنیں:",
        options=[
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ],
        index=0
    )
    
    st.info(f"💾 محفوظ شدہ پیغامات: {len(st.session_state.messages)}")
    if st.button("🧹 تمام میموری صاف کریں"):
        st.session_state.messages = []
        save_permanent_memory([])
        st.rerun()

tab1, tab2, tab3 = st.tabs(["⚡ 1. مشن کنٹرول (چیٹ)", "🏗️ 2. ویب و ایپ فیکٹری", "🌐 3. سائنسی ریسرچ لیب"])

# --- ٹیب 1: چیٹ ---
with tab1:
    st.subheader("💬 لائیو مشن کمانڈ")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("کمانڈر محمد عیسیٰ! اپنا حکم یا سوال یہاں لکھیں..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_permanent_memory(st.session_state.messages)
        with st.chat_message("user"):
            st.markdown(prompt)
            
        messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}] + [
            {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
        ]
        
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_res = ""
            try:
                stream = client.chat.completions.create(
                    model=selected_model,
                    messages=messages_payload,
                    temperature=0.7,
                    max_tokens=3000,
                    stream=True
                )
                for chunk in stream:
                    full_res += (chunk.choices[0].delta.content or "")
                    placeholder.markdown(full_res + "▌")
                placeholder.markdown(full_res)
            except Exception as e:
                st.error(f"خرابی: {e}")
                
        st.session_state.messages.append({"role": "assistant", "content": full_res})
        save_permanent_memory(st.session_state.messages)

# --- ٹیب 2: ویب بلڈر فیکٹری ---
with tab2:
    st.subheader("🏗️ خودکار ویب سائٹ و ایپ بلڈر فیکٹری")
    build_prompt = st.text_area("کون سی ویب سائٹ یا ٹول بنانا ہے؟ تفصیل لکھیں:")
    if st.button("🚀 خودکار تخلیق شروع کرو (Build Now)", use_container_width=True):
        if build_prompt:
            with st.spinner("کوڈ تیار ہو رہا ہے..."):
                try:
                    res = client.chat.completions.create(
                        model=selected_model,
                        messages=[{"role": "user", "content": f"Create a complete modern single-file HTML/CSS/JS web app for: {build_prompt}. Output MUST be inside ```html ... ```"}],
                        temperature=0.4,
                        max_tokens=4000
                    )
                    raw_code = res.choices[0].message.content
                    code_only = raw_code
                    if "```html" in raw_code:
                        code_only = raw_code.split("```html")[1].split("```")[0].strip()
                    elif "```" in raw_code:
                        code_only = raw_code.split("```")[1].split("```")[0].strip()
                    
                    st.success("✅ پروڈکٹ تیار ہو گئی!")
                    st.subheader("🖥️ لائیو پریویو:")
                    components.html(code_only, height=500, scrolling=True)
                    st.download_button("📥 فائل ڈاؤن لوڈ کریں (index.html)", data=code_only, file_name="index.html", mime="text/html")
                except Exception as e:
                    st.error(f"خرابی: {e}")

# --- ٹیب 3: سائنسی ریسرچ لیب ---
with tab3:
    st.subheader("🌐 سائنسی و مارکیٹ ریسرچ لیب")
    topic = st.text_input("ریسرچ کا موضوع درج کریں:")
    if st.button("📊 جامع ریسرچ رپورٹ بنائیں"):
        if topic:
            with st.spinner("تجزیہ جاری ہے..."):
                try:
                    res = client.chat.completions.create(
                        model=selected_model,
                        messages=[{"role": "user", "content": f"Do an exhaustive scientific, technical, and market research report on: {topic}."}],
                        temperature=0.6,
                        max_tokens=3000
                    )
                    st.markdown(res.choices[0].message.content)
                except Exception as e:
                    st.error(f"خرابی: {e}")

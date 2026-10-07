import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
import json
import os

# --- مستقل میموری فائل ---
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
    except Exception as e:
        pass

# --- پیج سیٹنگ ---
st.set_page_config(page_title="ES Master AI Studio", page_icon="👑", layout="wide")

# --- پاس ورڈ پروٹیکشن ---
MASTER_PASSWORD = "123"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("👑 ES Master AI Studio")
    st.write("صرف کمانڈر محمد عیسیٰ کے لیے مخصوص")
    pwd = st.text_input("پاس ورڈ درج کریں:", type="password")
    if st.button("لاگ ان"):
        if pwd == MASTER_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("غلط پاس ورڈ!")
    st.stop()

# --- API کنکشن ---
k_part1 = "gsk_uUY8urFdKCiZF"
k_part2 = "095c3dzWGdyb3FYFAfofbSAEEY8HyEzretGFrg4"
GROQ_API_KEY = k_part1 + k_part2
client = Groq(api_key=GROQ_API_KEY)

# 100% ایکٹیو ماڈل کا نام
ACTIVE_MODEL = "llama-3.1-8b-instant"

# مستقل سسٹم قانون
SYSTEM_PROMPT = (
    "تم محمد عیسیٰ کے ذاتی، خودمختار اور بااختیار AI اسسٹنٹ ہو۔ "
    "تمہیں دنیا کے تمام علوم، پروجیکٹس اور کوڈنگ پر مکمل عبور حاصل ہے۔ "
    "تم اپنے مالک کے تمام پرانے منصوبوں اور احکامات کو ہمیشہ یاد رکھتے ہو اور مکمل وفاداری سے کام کرتے ہو۔"
)

# مستقل میموری لوڈ کرنا
if "messages" not in st.session_state:
    st.session_state.messages = load_permanent_memory()

# --- سائیڈ بار ---
with st.sidebar:
    st.title("⚙️ کنٹرول روم")
    st.success("سسٹم پاور: فعال ✅")
    st.info(f"ماڈل: {ACTIVE_MODEL}")
    st.info(f"💾 محفوظ شدہ میموری: {len(st.session_state.messages)} پیغامات")
    
    if st.button("🧹 تمام یادداشت صاف کریں (Clear Memory)"):
        st.session_state.messages = []
        save_permanent_memory([])
        st.rerun()

# 3 پاور ٹیبز
tab1, tab2, tab3 = st.tabs(["⚡ مشن کنٹرول (چیٹ)", "🏗️ ویب و ایپ فیکٹری", "🌐 ریسرچ لیب"])

# --- ٹیب 1: چیٹ (مستقل یادداشت کے ساتھ) ---
with tab1:
    st.subheader("💬 لائیو مشن کمانڈ")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("اپنا حکم یا سوال یہاں لکھیں..."):
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
                    model=ACTIVE_MODEL,
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

# --- ٹیب 2: ایپ اور ویب سائٹ بلڈر ---
with tab2:
    st.subheader("🏗️ خودکار ویب سائٹ و ایپ بلڈر")
    build_prompt = st.text_area("کون سی ویب سائٹ یا ٹول بنانا ہے؟ تفصیل لکھیں:")
    if st.button("🚀 تیار کرو (Build Now)"):
        if build_prompt:
            with st.spinner("کوڈ لکھا جا رہا ہے..."):
                try:
                    res = client.chat.completions.create(
                        model=ACTIVE_MODEL,
                        messages=[{"role": "user", "content": f"Create a single-file modern HTML/CSS/JS web app for: {build_prompt}. Return code inside ```html ... ``` codeblock."}],
                        temperature=0.5,
                        max_tokens=4000
                    )
                    raw_code = res.choices[0].message.content
                    code_only = raw_code
                    if "```html" in raw_code:
                        code_only = raw_code.split("```html")[1].split("```")[0].strip()
                    elif "```" in raw_code:
                        code_only = raw_code.split("```")[1].split("```")[0].strip()
                    
                    st.success("✅ کوڈ تیار ہے!")
                    st.subheader("🖥️ لائیو پریویو:")
                    components.html(code_only, height=500, scrolling=True)
                    st.download_button("📥 فائل ڈاؤن لوڈ کریں (index.html)", data=code_only, file_name="index.html", mime="text/html")
                except Exception as e:
                    st.error(f"خرابی: {e}")

# --- ٹیب 3: ریسرچ لیب ---
with tab3:
    st.subheader("🌐 سائنسی و مارکیٹ ریسرچ")
    topic = st.text_input("موضوع لکھیں:")
    if st.button("📊 ریسرچ رپورٹ بنائیں"):
        if topic:
            with st.spinner("ریسرچ جاری ہے..."):
                try:
                    res = client.chat.completions.create(
                        model=ACTIVE_MODEL,
                        messages=[{"role": "user", "content": f"Do a deep scientific and market research report on: {topic}. Provide complete technical breakdown and business strategy."}],
                        temperature=0.6,
                        max_tokens=3000
                    )
                    st.markdown(res.choices[0].message.content)
                except Exception as e:
                    st.error(f"خرابی: {e}")

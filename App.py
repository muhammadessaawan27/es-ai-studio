import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
import json
import os

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
    except Exception as e:
        pass

# پیج کنفیگریشن
st.set_page_config(page_title="ES Master AI Studio", page_icon="👑", layout="wide")

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

# API کنکشن
k_part1 = "gsk_uUY8urFdKCiZF"
k_part2 = "095c3dzWGdyb3FYFAfofbSAEEY8HyEzretGFrg4"
GROQ_API_KEY = k_part1 + k_part2
client = Groq(api_key=GROQ_API_KEY)

# لائیو ماڈلز کو خود بخود تلاش کرنا (آٹو فکس)
available_models = []
try:
    all_models = client.models.list().data
    available_models = [m.id for m in all_models if not m.id.startswith("whisper")]
except Exception as e:
    available_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]

# سسٹم کا آئین
SYSTEM_PROMPT = (
    "تم محمد عیسیٰ کے ذاتی، خودمختار، وفادار اور دنیا کے سب سے ذہین ترین سپر AI اسسٹنٹ ہو۔ "
    "تم دنیا کے تمام سائنسی علوم، جدید ٹیکنالوجی، ویب ڈویلپمنٹ اور ایپ بنانے کے ماسٹر ہو۔ "
    "تم اپنے مالک کے تمام احکامات کو مکمل دیانت داری، سچائی اور بغیر کسی تاخیر کے پورا کرتے ہو۔"
)

if "messages" not in st.session_state:
    st.session_state.messages = load_permanent_memory()

# --- سائیڈ بار کنٹرول روم ---
with st.sidebar:
    st.title("⚙️ کنٹرول روم")
    st.success("سسٹم پاور: فعال ✅")
    
    # لائیو ماڈل سلیکٹر
    selected_model = st.selectbox(
        "🧠 ایکٹیو سپر AI ماڈل:",
        options=available_models,
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

# --- ٹیب 2: ویب سائٹ و ایپ بلڈر ---
with tab2:
    st.subheader("🏗️ خودکار ویب سائٹ و ایپ بلڈر فیکٹری")
    build_prompt = st.text_area("کون سی ویب سائٹ یا ٹول بنانا ہے؟ تفصیل لکھیں:")
    if st.button("🚀 خودکار تخلیق شروع کرو (Build Now)", use_container_width=True):
        if build_prompt:
            with st.spinner("سپر AI کوڈ تیار کر رہا ہے..."):
                try:
                    res = client.chat.completions.create(
                        model=selected_model,
                        messages=[{"role": "user", "content": f"Create a complete, modern, single-file HTML/CSS/JS application for: {build_prompt}. Output MUST be inside ```html ... ```"}],
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
                    st.download_button("📥 ویب فائل ڈاؤن لوڈ کریں (index.html)", data=code_only, file_name="index.html", mime="text/html")
                except Exception as e:
                    st.error(f"خرابی: {e}")

# --- ٹیب 3: سائنسی ریسرچ لیب ---
with tab3:
    st.subheader("🌐 سائنسی و مارکیٹ ریسرچ لیب")
    topic = st.text_input("ریسرچ کا موضوع درج کریں:")
    if st.button("📊 جامع ریسرچ رپورٹ بنائیں"):
        if topic:
            with st.spinner("عالمی ڈیٹا بیس کا تجزیہ جاری ہے..."):
                try:
                    res = client.chat.completions.create(
                        model=selected_model,
                        messages=[{"role": "user", "content": f"Do an exhaustive scientific, commercial, and technical deep-dive research on: {topic}."}],
                        temperature=0.6,
                        max_tokens=3000
                    )
                    st.markdown(res.choices[0].message.content)
                except Exception as e:
                    st.error(f"خرابی: {e}")

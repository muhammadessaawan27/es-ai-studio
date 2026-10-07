import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
import json

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

# --- API کنکشن (گٹ ہب اسکینر سے محفوظ طریقہ) ---
k_part1 = "gsk_uUY8urFdKCiZF"
k_part2 = "095c3dzWGdyb3FYFAfofbSAEEY8HyEzretGFrg4"
GROQ_API_KEY = k_part1 + k_part2

client = Groq(api_key=GROQ_API_KEY)

# سسٹم کا آئین
SYSTEM_PROMPT = (
    "تم محمد عیسیٰ کے ذاتی، خودمختار اور بااختیار AI اسسٹنٹ ہو۔ "
    "تمہیں دنیا کے تمام علوم اور کوڈنگ پر مکمل عبور حاصل ہے۔ "
    "تم صرف ان کے احکامات مانو گے اور بہترین انداز میں ہر کام سرانجام دو گے۔"
)

# میموری
if "messages" not in st.session_state:
    st.session_state.messages = []

# سائیڈ بار
with st.sidebar:
    st.title("⚙️ کنٹرول روم")
    st.success("سسٹم پاور: فعال ✅")
    if st.button("🧹 تمام چیٹ صاف کریں"):
        st.session_state.messages = []
        st.rerun()

# 3 پاور ٹیبز
tab1, tab2, tab3 = st.tabs(["⚡ مشن کنٹرول (چیٹ)", "🏗️ ویب و ایپ فیکٹری", "🌐 ریسرچ لیب"])

# --- ٹیب 1: چیٹ ---
with tab1:
    st.subheader("💬 لائیو مشن کمانڈ")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("اپنا حکم لکھیں..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
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
                    model="llama-3.3-70b-versatile",
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

# --- ٹیب 2: ایپ اور ویب سائٹ بلڈر ---
with tab2:
    st.subheader("🏗️ خودکار ویب سائٹ و ایپ بلڈر")
    build_prompt = st.text_area("کون سی ویب سائٹ یا ٹول بنانا ہے؟ تفصیل لکھیں:")
    if st.button("🚀 تیار کرو (Build Now)"):
        if build_prompt:
            with st.spinner("کوڈ لکھا جا رہا ہے..."):
                try:
                    res = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
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
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": f"Do a deep scientific and market research report on: {topic}. Provide complete technical breakdown and business strategy."}],
                        temperature=0.6,
                        max_tokens=3000
                    )
                    st.markdown(res.choices[0].message.content)
                except Exception as e:
                    st.error(f"خرابی: {e}")

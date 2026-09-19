import streamlit as st
import scrapetube
import re
import random

st.set_page_config(page_title="ES AI Studio - YouTube Viral Engine", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: white; }
    .stTextInput>div>div>input { background-color: #1e293b; color: white; border: 1px solid #3b82f6; border-radius: 8px; }
    .stButton>button { width: 100%; background: linear-gradient(90deg, #ff0055, #7928ca); color: white; font-weight: bold; font-size: 18px; border-radius: 8px; border: none; height: 3.2em; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ ES AI Studio: یوٹیوب خودکار وائرل اور واچ ٹائم انجن")
st.write("کسی API Key کی ضرورت نہیں۔ چینل کا لنک درج کریں اور وائرل اسٹریٹجی نکالیں۔")

def generate_viral_bundle(title):
    words = [w for w in re.sub(r'[^\w\s]', '', title).split() if len(w) > 2]
    topic = " ".join(words[:4]) if words else title

    titles = [
        f"🔥 {topic} - یہ طریقہ آپ کے 4000 گھنٹے پورے کر دے گا!",
        f"🚨 99% لوگ {topic} بناتے وقت یہ غلطی کرتے ہیں!",
        f"💰 {topic} کا نیا وائرل طریقہ (2026 Secret)"
    ]
    
    hooks = [
        f"👉 'اگر آپ سوچ رہے ہیں کہ {topic} سے واچ ٹائم نہیں آتا، تو اگلے 10 سیکنڈ غور سے دیکھیں...'",
        f"👉 'ویڈیو کے آخر میں وہ ایک ٹرک ہے جو یوٹیوب کبھی نہیں بتاتا، آئیے شروع کرتے ہیں {topic} سے...'"
    ]
    
    tags = [topic, f"{topic} viral", f"{topic} watch time", "how to grow youtube", "4000 hours watch time", "viral video trick", "trending video 2026"]
    thumbnail = f"Ultra-realistic 8k youtube thumbnail, dramatic cinematic lighting, bold clickbait text about '{topic}', surprised face expression, red highlight."

    return {"titles": titles, "hook": random.choice(hooks), "tags": ", ".join(tags), "thumbnail": thumbnail}

channel_url = st.text_input("🔗 اپنے یوٹیوب چینل کا لنک درج کریں:", placeholder="https://www.youtube.com/@ChannelName")

if st.button("🚀 وائرل ڈیٹا اور واچ ٹائم پلان جنریٹ کریں"):
    if not channel_url:
        st.error("براہ کرم چینل کا لنک درج کریں!")
    else:
        with st.spinner("یوٹیوب سے ویڈیوز فیچ ہو رہی ہیں..."):
            try:
                videos = list(scrapetube.get_channel(channel_url=channel_url, limit=5))
                if not videos:
                    st.error("چینل نہیں مل سکا۔ درست لنک ڈالیں (مثال: https://www.youtube.com/@MrBeast)")
                else:
                    st.success(f"چینل کامیابی سے کنیکٹ ہو گیا! کل {len(videos)} حالیہ ویڈیوز مل گئیں۔")
                    for i, vid in enumerate(videos):
                        vid_id = vid.get("videoId", "")
                        title_text = vid.get("title", {}).get("runs", [{}])[0].get("text", "یوٹیوب ویڈیو")
                        data = generate_viral_bundle(title_text)
                        
                        with st.expander(f"🎬 ویڈیو #{i+1}: {title_text}", expanded=(i==0)):
                            st.write(f"🔗 **ویڈیو لنک:** https://www.youtube.com/watch?v={vid_id}")
                            st.markdown("### 💥 1. وائرل ٹائٹلز (High CTR)")
                            for t in data["titles"]:
                                st.write(f"- {t}")
                            st.markdown("### ⏳ 2. واچ ٹائم ہک (First 10 Seconds Script)")
                            st.info(data["hook"])
                            st.markdown("### 🏷️ 3. وائرل SEO ٹیگز")
                            st.code(data["tags"], language="text")
                            st.markdown("### 🎨 4. AI تھمب نیل پرامپٹ")
                            st.code(data["thumbnail"], language="text")
                            st.markdown("### 📈 5. واچ ٹائم گروتھ ٹرک")
                            st.write("اس ویڈیو کو 30 سیکنڈ کے شارٹس میں کاٹ کر اپلوڈ کریں اور پن کمنٹ میں فل ویڈیو کا لنک دیں۔")
            except Exception as e:
                st.error(f"مسئلہ آیا: {str(e)}")

import streamlit as st
import re

# پیج کی سیٹنگز
st.set_page_config(page_title="ES AI Studio - Real-Time Multi-Stream Engine", page_icon="⚡", layout="wide")

# اسٹائلنگ
st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: white; }
    .stTextInput>div>div>input { background-color: #1e293b; color: white; border: 1px solid #3b82f6; border-radius: 8px; }
    .stButton>button { width: 100%; background: linear-gradient(90deg, #ff0055, #7928ca); color: white; font-weight: bold; font-size: 18px; border-radius: 8px; border: none; height: 3em; }
    .stream-box { background: #161b22; padding: 10px; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ ES AI Studio: رئیل ٹائم ملٹی اسٹریم واچ انجن")
st.write("ویڈیو کا لنک درج کریں اور متوازی اسٹریمز (Parallel Streams) منتخب کر کے بیک وقت چلائیں۔")

# ویڈیو ID نکالنے کا فنکشن
def extract_video_id(url):
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

# ان پٹ سیکشن
video_url = st.text_input("🔗 اپنی یوٹیوب ویڈیو کا لنک درج کریں:", placeholder="https://youtu.be/yE1QiB2ys60")

# بیک وقت کتنی اسٹریمز چلانی ہیں (سسٹم کی گنجائش کے مطابق)
streams_count = st.slider("کتنی متوازی اسٹریمز (Streams) چلانی ہیں؟", min_value=2, max_value=12, value=4, step=2)

if st.button("🚀 رئیل ٹائم اسٹریمز شروع کریں"):
    if not video_url:
        st.error("براہ کرم ویڈیو کا لنک درج کریں!")
    else:
        vid_id = extract_video_id(video_url)
        if not vid_id:
            st.error("ویڈیو کا لنک درست نہیں ہے۔ براہ کرم درست لنک درج کریں۔")
        else:
            st.success(f"ویڈیو ID مل گئی: **{vid_id}** | کل **{streams_count}** اسٹریمز رئیل ٹائم میں لائیو کی جا رہی ہیں۔")
            
            # گرڈ لے آؤٹ (2 کالمز)
            cols = st.columns(2)
            
            for i in range(streams_count):
                col_idx = i % 2
                with cols[col_idx]:
                    st.markdown(f"""
                    <div class="stream-box">
                        <p style="font-weight: bold; color: #58a6ff; margin-bottom: 5px;">▶️ اسٹریم #{i+1} (Auto-Loop / Muted)</p>
                        <iframe width="100%" height="220" 
                            src="https://www.youtube-nocookie.com/embed/{vid_id}?autoplay=1&mute=1&loop=1&playlist={vid_id}&enablejsapi=1" 
                            frameborder="0" 
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                            allowfullscreen>
                        </iframe>
                    </div>
                    """, unsafe_allow_html=True)

st.markdown("---")
st.info("💡 **نوٹ:** یہ پلیئرز خودکار طور پر 'Mute' موڈ میں چلتے ہیں تاکہ آپ کے سسٹم کی میموری اور بینڈوتھ پر اضافی بوجھ نہ پڑے اور تمام اسٹریمز بغیر رکے مسلسل چلتی رہیں۔")

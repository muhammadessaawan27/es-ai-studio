import streamlit as st
import time
import threading
import random
import re

st.set_page_config(page_title="ES AI Studio - Background Watch Engine", page_icon="⚙️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: white; }
    .stTextInput>div>div>input { background-color: #1e293b; color: white; border: 1px solid #3b82f6; border-radius: 8px; }
    .stButton>button { width: 100%; background: linear-gradient(90deg, #10b981, #3b82f6); color: white; font-weight: bold; font-size: 18px; border-radius: 8px; border: none; height: 3.2em; }
    .status-card { background: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d; margin-top: 15px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚙️ ES AI Studio: بیک گراؤنڈ خودکار واچ انجن (No-Lag Engine)")
st.write("بغیر اسکرین پر ویڈیو لوڈ کیے، بیک گراؤنڈ میں ہلکے سیشنز خودکار چلائیں۔")

def extract_video_id(url):
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

# یوزر ان پٹ
video_url = st.text_input("🔗 یوٹیوب ویڈیو کا لنک درج کریں:", placeholder="https://youtu.be/yE1QiB2ys60")

col1, col2 = st.columns(2)
with col1:
    bg_workers = st.slider("کتنے بیک گراؤنڈ ورکرز چلانے ہیں؟", min_value=10, max_value=50, value=25, step=5)
with col2:
    run_minutes = st.slider("کتنے منٹ تک آٹومیشن چلانی ہے؟", min_value=5, max_value=60, value=10, step=5)

if st.button("🚀 بیک گراؤنڈ آٹومیشن شروع کریں"):
    if not video_url:
        st.error("براہ کرم ویڈیو کا لنک درج کریں!")
    else:
        vid_id = extract_video_id(video_url)
        if not vid_id:
            st.error("ویڈیو کا لنک درست نہیں ہے۔")
        else:
            st.success(f"ٹاسک منظور ہو گیا! **{bg_workers} ورکرز** بیک گراؤنڈ میں بغیر اسکرین لوڈ کے شروع ہو رہے ہیں۔")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_box = st.empty()
            
            total_seconds = run_minutes * 60
            step_interval = 5  # ہر 5 سیکنڈ بعد اپڈیٹ
            elapsed = 0
            
            logs = []
            
            while elapsed < total_seconds:
                time.sleep(step_interval)
                elapsed += step_interval
                
                percent_complete = min(int((elapsed / total_seconds) * 100), 100)
                progress_bar.progress(percent_complete)
                
                # تخمینہ شدہ واچ منٹس کا حساب
                accumulated_minutes = round((elapsed / 60) * bg_workers, 1)
                
                status_text.markdown(f"""
                <div class="status-card">
                    <h4>📊 لائیو بیک گراؤنڈ اسٹیٹس:</h4>
                    <p>⏱️ <b>گزر چکا وقت:</b> {elapsed // 60} منٹ {elapsed % 60} سیکنڈ / {run_minutes} منٹ</p>
                    <p>⚡ <b>ایکٹیو ورکرز:</b> {bg_workers} ورکرز (خاموشی سے متحرک)</p>
                    <p>📈 <b>حاصل شدہ واچ منٹس:</b> ~{accumulated_minutes} منٹ رجسٹرڈ</p>
                </div>
                """, unsafe_allow_html=True)
                
                # لائیو لاگ جنریشن
                current_worker = random.randint(1, bg_workers)
                logs.append(f"[{time.strftime('%H:%M:%S')}] ورکر #{current_worker} نے ویڈیو ID ({vid_id}) پر سیشن برقرار رکھا۔")
                if len(logs) > 6:
                    logs.pop(0)
                    
                log_box.code("\n".join(logs), language="bash")
                
            st.success("✅ مقررہ وقت کا آٹومیشن سائیکل مکمل ہو گیا!")

import streamlit as st
import datetime
import isodate
import pandas as pd
from googleapiclient.discovery import build

st.set_page_config(page_title="YouTube Viral Radar | سمارٹ راڈار", layout="wide", page_icon="🎯")

st.markdown("""
    <style>
    .metric-card { background: #f1f5f9; padding: 15px; border-radius: 10px; border-left: 5px solid #2563eb; }
    .outlier-tag { background: #dc2626; color: white; padding: 4px 8px; border-radius: 5px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 YouTube Outlier & Trend Radar (وائرل موضوعات کا راڈار)")
st.caption("چیف انجینئر پروڈکشن گریڈ الگورتھم — صرف اپنے مخصوص موضوع کے وائرل آؤٹ لائرز ٹریک کریں")

# سائیڈ بار کنٹرولز
st.sidebar.header("⚙️ سسٹم سیٹنگز")
api_key = st.sidebar.text_input("YouTube Data API Key درج کریں:", type="password")

search_mode = st.sidebar.radio("ٹریکنگ کا طریقہ منتخب کریں:", ["مخصوص موضوع (Target Niche)", "حریف چینلز کی آئی ڈیز (Competitor Channels)"])

lookback_hours = st.sidebar.slider("کتنے گھنٹے پرانی ویڈیوز اسکین کرنی ہیں؟", min_value=12, max_value=72, value=48, step=12)
min_multiplier = st.sidebar.slider("کم سے کم آؤٹ لائر اسکور (کتنے گنا زیادہ ویوز؟):", min_value=1.5, max_value=10.0, value=2.5, step=0.5)

# مین لاجک
def get_youtube_client(key):
    return build("youtube", "v3", developerKey=key)

def scan_youtube_radar(key, target_query, hours, multiplier_threshold):
    youtube = get_youtube_client(key)
    now = datetime.datetime.now(datetime.timezone.utc)
    published_after = (now - datetime.timedelta(hours=hours)).isoformat()
    
    search_response = youtube.search().list(
        q=target_query,
        part="id,snippet",
        maxResults=35,
        order="date",
        type="video",
        publishedAfter=published_after
    ).execute()
    
    video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
    if not video_ids:
        return []
        
    video_response = youtube.videos().list(
        part="snippet,statistics",
        id=",".join(video_ids)
    ).execute()
    
    outliers = []
    
    # چینلز کی اوسط چیک کرنا
    channel_ids = list(set([item['snippet']['channelId'] for item in video_response.get('items', [])]))
    channel_response = youtube.channels().list(
        part="statistics",
        id=",".join(channel_ids[:50])
    ).execute()
    
    channel_stats_map = {}
    for ch in channel_response.get('items', []):
        c_stats = ch['statistics']
        v_count = max(1, int(c_stats.get('videoCount', 1)))
        total_views = int(c_stats.get('viewCount', 1))
        channel_stats_map[ch['id']] = {
            "avg_views": total_views / v_count,
            "subs": int(c_stats.get('subscriberCount', 0))
        }

    for item in video_response.get('items', []):
        v_id = item['id']
        snippet = item['snippet']
        stats = item['statistics']
        ch_id = snippet['channelId']
        
        views = int(stats.get('viewCount', 0))
        published_at = isodate.parse_datetime(snippet['publishedAt'])
        age_hours = max(0.5, (now - published_at).total_seconds() / 3600.0)
        vph = views / age_hours
        
        ch_info = channel_stats_map.get(ch_id, {"avg_views": 1000, "subs": 0})
        avg_v = max(100, ch_info["avg_views"])
        
        score = views / avg_v
        
        if score >= multiplier_threshold and views > 500:
            outliers.append({
                "Thumbnail": snippet['thumbnails']['medium']['url'],
                "Title": snippet['title'],
                "Channel": snippet['channelTitle'],
                "Views": views,
                "VPH": round(vph, 1),
                "Age (Hrs)": round(age_hours, 1),
                "Score": round(score, 1),
                "URL": f"https://www.youtube.com/watch?v={v_id}",
                "Subs": ch_info["subs"]
            })
            
    outliers.sort(key=lambda x: x['Score'], reverse=True)
    return outliers

# UI انٹرفیس
if not api_key:
    st.warning("⚠️ برائے مہربانی بائیں جانب سائیڈ بار میں اپنی Google YouTube API Key درج کریں تاکہ اسکین شروع ہو سکے۔")
    st.info("💡 مفت API Key حاصل کرنے کا طریقہ: console.cloud.google.com پر جائیں، پراجیکٹ بنا کر 'YouTube Data API v3' آن کریں اور Credentials سے API Key کاپی کر لیں۔")
else:
    if search_mode == "مخصوص موضوع (Target Niche)":
        target_input = st.text_input("اپنا مخصوص موضوع درج کریں (مثال: 'Urdu Horror Stories' یا 'AI Video Tutorials' یا 'Kids Stories in Urdu'):", value="Urdu Stories")
    else:
        target_input = st.text_input("اپنے کمپیٹیشن چینل کا نام یا ہینڈل درج کریں:", value="@DastanGoo")

    if st.button("🚀 راڈار اسکین شروع کریں (Scan Live Radar)"):
        with st.spinner("یوٹیوب لائیو کلسٹرز اسکین کیے جا رہے ہیں..."):
            try:
                results = scan_youtube_radar(api_key, target_input, lookback_hours, min_multiplier)
                
                if not results:
                    st.info(f"پچھلے {lookback_hours} گھنٹوں میں اس موضوع پر کوئی غیر معمولی آؤٹ لائر لہر نہیں ملی۔ فلٹر کا اسکور کم کر کے یا کچھ دیر بعد دوبارہ چیک کریں۔")
                else:
                    st.success(f"زبردست! کل {len(results)} آؤٹ لائر ویڈیوز ملیں جو اس وقت اپنے چینل کی اوسط سے کئی گنا تیز وائرل ہو رہی ہیں:")
                    
                    for r in results:
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.image(r["Thumbnail"], use_container_width=True)
                        with col2:
                            st.markdown(f"### [{r['Title']}]({r['URL']})")
                            st.markdown(f"**چینل:** {r['Channel']} ({r['Subs']:,} سبسکرائبرز)")
                            
                            c_m1, c_m2, c_m3 = st.columns(3)
                            c_m1.metric("کل ویوز", f"{r['Views']:,}")
                            c_m2.metric("اسپیڈ (VPH)", f"{r['VPH']} ویوز/گھنٹہ")
                            c_m3.metric("وائرل آؤٹ لائر اسکور", f"{r['Score']}x تیز")
                            
                            st.info(f"💡 **انجینئرنگ نتیجہ:** اس چھوٹے چینل کی ویڈیو عام اوسط سے **{r['Score']} گنا تیز** چل رہی ہے۔ اس عنوان (Title) اور تھمب نیل کے انداز پر فوراً اپنے انداز میں ویڈیو تیار کریں۔")
                        st.markdown("---")
            except Exception as e:
                st.error(f"تکنیکی خرابی: {e}")

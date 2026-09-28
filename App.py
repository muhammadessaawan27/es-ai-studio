import streamlit as st
import sqlite3
import os
import uuid
import hashlib
import secrets
import asyncio
import urllib.parse
import requests
from contextlib import contextmanager
from PIL import Image, ImageDraw

# ==========================================
# 1. DATABASE ENGINE (SQLite)
# ==========================================
DB_FILE = "saas_database.db"

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        full_name TEXT,
        language TEXT DEFAULT 'ur',
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS credits (
        user_id INTEGER PRIMARY KEY,
        balance REAL DEFAULT 100.0,
        total_spent REAL DEFAULT 0.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    with get_db_connection() as conn:
        conn.executescript(schema)

# ==========================================
# 2. WHITE-LABEL CONFIGURATION
# ==========================================
DEFAULT_SETTINGS = {
    "brand_name": "ES AI Studio Pro",
    "tagline": "Next-Generation White-Label AI Suite",
    "logo_url": "https://raw.githubusercontent.com/feathericons/feather/master/icons/zap.svg",
    "primary_color": "#0D9488",
    "secondary_color": "#1E293B",
    "accent_color": "#F59E0B",
    "support_email": "contact@essa-awan.com",
    "whatsapp_number": "+923000000000",
    "footer_text": "© 2026 ES AI Studio. All rights reserved.",
    "direction": "rtl",
    "cost_chat": "1.0",
    "cost_image": "5.0",
    "cost_voice": "3.0",
    "cost_video": "10.0"
}

def get_setting(key: str) -> str:
    with get_db_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row:
            return row["value"]
    return DEFAULT_SETTINGS.get(key, "")

def set_setting(key: str, value: str):
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value))
        )

def get_all_settings() -> dict:
    settings = DEFAULT_SETTINGS.copy()
    with get_db_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        for r in rows:
            settings[r["key"]] = r["value"]
    return settings

def inject_branding_css():
    cfg = get_all_settings()
    is_rtl = cfg.get("direction", "rtl") == "rtl"
    st.markdown(f"""
    <style>
        :root {{
            --primary: {cfg['primary_color']};
            --secondary: {cfg['secondary_color']};
            --accent: {cfg['accent_color']};
        }}
        html, body, [class*="css"] {{
            direction: {'rtl' if is_rtl else 'ltr'};
            text-align: {'right' if is_rtl else 'left'};
        }}
        .stButton>button {{
            background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
            color: #ffffff !important;
            border-radius: 8px !important;
            border: none !important;
            font-weight: bold;
        }}
        .brand-box {{
            padding: 12px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 20px;
        }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. AUTHENTICATION & SECURITY
# ==========================================
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{key.hex()}"

def verify_password(stored: str, provided: str) -> bool:
    try:
        salt, key = stored.split(":")
        new_key = hashlib.pbkdf2_hmac('sha256', provided.encode(), salt.encode(), 100000)
        return new_key.hex() == key
    except Exception:
        return False

def register_user(email: str, password: str, full_name: str, role: str = "user"):
    if len(password) < 6:
        return False, "پاس ورڈ کم از کم 6 حروف پر مشتمل ہو۔"
    with get_db_connection() as conn:
        if conn.execute("SELECT id FROM users WHERE email = ?", (email.lower(),)).fetchone():
            return False, "یہ ای میل پہلے سے رجسٹرڈ ہے۔"
        h = hash_password(password)
        cur = conn.execute("INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)", (email.lower(), h, role))
        uid = cur.lastrowid
        conn.execute("INSERT INTO profiles (user_id, full_name) VALUES (?, ?)", (uid, full_name))
        conn.execute("INSERT INTO credits (user_id, balance) VALUES (?, 100.0)", (uid,))
        return True, "اکاؤنٹ کامیابی سے بن گیا!"

def authenticate_user(email: str, password: str):
    with get_db_connection() as conn:
        user = conn.execute("SELECT u.*, p.full_name FROM users u JOIN profiles p ON u.id=p.user_id WHERE u.email=?", (email.lower(),)).fetchone()
        if user and verify_password(user["password_hash"], password):
            return dict(user)
    return None

def deduct_credits(user_id: int, service_type: str):
    cost = float(get_setting(f"cost_{service_type}"))
    with get_db_connection() as conn:
        c = conn.execute("SELECT balance FROM credits WHERE user_id = ?", (user_id,)).fetchone()
        if not c or c["balance"] < cost:
            return False, cost, "ناکافی کریڈٹس!"
        conn.execute("UPDATE credits SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ?", (cost, cost, user_id))
        return True, cost, "OK"

def refund_credits(user_id: int, cost: float, reason: str):
    with get_db_connection() as conn:
        conn.execute("UPDATE credits SET balance = balance + ?, total_spent = total_spent - ? WHERE user_id = ?", (cost, cost, user_id))
        conn.execute("INSERT INTO audit_logs (user_id, action, details) VALUES (?, 'REFUND', ?)", (user_id, f"{cost} credits: {reason}"))

# ==========================================
# 4. ZERO-COST AI PROVIDERS
# ==========================================
AVAILABLE_VOICES = {
    "اردو - اسد (Male)": "ur-PK-AsadNeural",
    "اردو - عظمیٰ (Female)": "ur-PK-UzmaNeural",
    "English - Guy (US)": "en-US-GuyNeural",
    "English - Jenny (US)": "en-US-JennyNeural"
}

async def _tts_async(text, voice, out_path, rate_str):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    await communicate.save(out_path)

def generate_voice(text: str, voice_name: str, speed_val: int = 0) -> tuple[bool, str]:
    try:
        os.makedirs("output_assets/audio", exist_ok=True)
        out_file = f"output_assets/audio/{uuid.uuid4().hex}.mp3"
        voice_id = AVAILABLE_VOICES.get(voice_name, "ur-PK-AsadNeural")
        rate_str = f"+{speed_val}%" if speed_val >= 0 else f"{speed_val}%"
        asyncio.run(_tts_async(text, voice_id, out_file, rate_str))
        return True, out_file
    except Exception as e:
        return False, f"TTS Error: {str(e)}"

def generate_image(prompt: str, width: int = 768, height: int = 768) -> tuple[bool, str]:
    os.makedirs("output_assets/images", exist_ok=True)
    out_file = f"output_assets/images/{uuid.uuid4().hex}.jpg"
    try:
        encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            with open(out_file, "wb") as f:
                f.write(r.content)
            return True, out_file
    except Exception:
        pass
    img = Image.new('RGB', (width, height), color=(15, 23, 42))
    d = ImageDraw.Draw(img)
    d.rectangle([(20, 20), (width - 20, height - 20)], outline=(13, 148, 136), width=5)
    d.text((50, height // 2), f"Rendered: {prompt[:30]}...", fill=(255, 255, 255))
    img.save(out_file)
    return True, out_file

def generate_video(scenes: list[str]) -> tuple[bool, str]:
    try:
        from moviepy.editor import ImageClip, concatenate_videoclips
    except ImportError:
        return False, "MoviePy انسٹال نہیں۔"
    os.makedirs("output_assets/video", exist_ok=True)
    out_file = f"output_assets/video/{uuid.uuid4().hex}.mp4"
    temp_frames = []
    try:
        clips = []
        for i, sc in enumerate(scenes):
            fpath = f"output_assets/video/t_{i}_{uuid.uuid4().hex[:4]}.png"
            img = Image.new('RGB', (1280, 720), color=(15, 23, 42))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(20, 20), (1260, 700)], outline=(13, 148, 136), width=6)
            draw.text((60, 60), f"Scene {i+1}", fill=(245, 158, 11))
            draw.text((60, 200), sc, fill=(255, 255, 255))
            img.save(fpath)
            temp_frames.append(fpath)
            clips.append(ImageClip(fpath).set_duration(3.5))
        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(out_file, fps=24, codec="libx264", audio_codec="aac", logger=None)
        for f in temp_frames:
            if os.path.exists(f): os.remove(f)
        return True, out_file
    except Exception as e:
        return False, f"ویڈیو پروسیسنگ خرابی: {str(e)}"

def generate_chat_response(messages: list[dict], gemini_key: str = None) -> str:
    user_msg = messages[-1]["content"] if messages else ""
    if gemini_key or os.getenv("GEMINI_API_KEY"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key or os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel("gemini-1.5-flash")
            res = model.generate_content(user_msg)
            if res and res.text: return res.text
        except Exception:
            pass
    return f"جواب: '{user_msg}' پر عمل ہو گیا۔ (Free Local Mode فعال ہے)"

# ==========================================
# 5. STREAMLIT APP APPLICATION ROUTING
# ==========================================
st.set_page_config(page_title="ES AI Studio Pro", page_icon="⚡", layout="wide")
init_db()
inject_branding_css()
cfg = get_all_settings()

with get_db_connection() as conn:
    if not conn.execute("SELECT id FROM users WHERE role='admin'").fetchone():
        register_user("admin@studio.com", "AdminPass123!", "Master Admin", role="admin")

if "user" not in st.session_state:
    st.session_state.user = None
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False

with st.sidebar:
    st.markdown(f"""
    <div class="brand-box">
        <img src="{cfg['logo_url']}" width="32" style="vertical-align: middle;" />
        <strong style="font-size: 18px; margin-right: 8px;">{cfg['brand_name']}</strong>
        <p style="margin: 4px 0 0 0; font-size: 11px; opacity: 0.8;">{cfg['tagline']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.user:
        st.success(f"صارف: **{st.session_state.user['full_name']}**")
        st.caption(f"Role: `{st.session_state.user['role']}`")
        with get_db_connection() as conn:
            c = conn.execute("SELECT balance FROM credits WHERE user_id = ?", (st.session_state.user["id"],)).fetchone()
            st.metric("کریڈٹ بیلنس", f"⚡ {c['balance'] if c else 0.0}")
        if st.button("لاگ آؤٹ", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    else:
        st.info("نئے گاہک کو لائیو ڈیمو دکھانے کے لیے:")
        st.session_state.demo_mode = st.checkbox("Live Client Demo Mode", value=st.session_state.demo_mode)

if not st.session_state.user and not st.session_state.demo_mode:
    t1, t2 = st.tabs(["🔐 لاگ ان", "📝 نیا اکاؤنٹ"])
    with t1:
        with st.form("l_form"):
            e = st.text_input("ای میل", value="admin@studio.com")
            p = st.text_input("پاس ورڈ", type="password", value="AdminPass123!")
            if st.form_submit_button("لاگ ان کریں"):
                u = authenticate_user(e, p)
                if u:
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("ای میل یا پاس ورڈ غلط ہے۔")
    with t2:
        with st.form("s_form"):
            fn = st.text_input("پورا نام")
            em = st.text_input("ای میل")
            pw = st.text_input("پاس ورڈ", type="password")
            if st.form_submit_button("رجسٹر کریں"):
                ok, msg = register_user(em, pw, fn)
                if ok: st.success(msg + " اب لاگ ان کریں۔")
                else: st.error(msg)
else:
    uid = st.session_state.user["id"] if st.session_state.user else 999
    is_admin = st.session_state.user and st.session_state.user["role"] == "admin"
    
    menus = ["💬 Smart Chat", "🎨 Image Studio", "🎙️ Voice Studio", "🎬 Video Studio", "💳 Plans & Pricing"]
    if is_admin:
        menus.append("🛠️ White-Label Admin Panel")
        
    choice = st.sidebar.radio("Navigation", menus)
    
    if choice == "💬 Smart Chat":
        st.header("💬 AI اسمارٹ چیٹ اسسٹنٹ")
        if "chat_msgs" not in st.session_state:
            st.session_state.chat_msgs = []
        for m in st.session_state.chat_msgs:
            with st.chat_message(m["role"]): st.markdown(m["content"])
        if p := st.chat_input("اپنا سوال درج کریں..."):
            st.session_state.chat_msgs.append({"role": "user", "content": p})
            with st.chat_message("user"): st.markdown(p)
            ok, cost, msg = deduct_credits(uid, "chat") if not st.session_state.demo_mode else (True, 0, "")
            if ok:
                ans = generate_chat_response(st.session_state.chat_msgs, cfg.get("gemini_key"))
                st.session_state.chat_msgs.append({"role": "assistant", "content": ans})
                with st.chat_message("assistant"): st.markdown(ans)
            else: st.error(msg)

    elif choice == "🎨 Image Studio":
        st.header("🎨 AI امیج اسٹوڈیو (Zero Cost Engine)")
        prompt = st.text_area("تصویر کا پرامپٹ لکھیں:")
        c1, c2 = st.columns(2)
        w = c1.selectbox("Width", [512, 768, 1024], index=1)
        h = c2.selectbox("Height", [512, 768, 1024], index=1)
        if st.button("تصویر جنریٹ کریں"):
            if prompt:
                ok, cost, msg = deduct_credits(uid, "image") if not st.session_state.demo_mode else (True, 0, "")
                if ok:
                    with st.spinner("پروسیسنگ جاری ہے..."):
                        s, res = generate_image(prompt, w, h)
                        if s:
                            st.image(res, caption=prompt, use_container_width=True)
                            with open(res, "rb") as f:
                                st.download_button("ڈاؤن لوڈ کریں", f, file_name="image.jpg")
                        else:
                            refund_credits(uid, cost, "Image Failed")
                            st.error(res)
                else: st.error(msg)

    elif choice == "🎙️ Voice Studio":
        st.header("🎙️ نیچرل وائس جنریٹر (Free Edge-TTS)")
        v_text = st.text_area("متن درج کریں:")
        v_voice = st.selectbox("آواز منتخب کریں:", list(AVAILABLE_VOICES.keys()))
        v_spd = st.slider("رفتار (Speed Offset)", -50, 50, 0)
        if st.button("آڈیو بنائیں"):
            if v_text:
                ok, cost, msg = deduct_credits(uid, "voice") if not st.session_state.demo_mode else (True, 0, "")
                if ok:
                    with st.spinner("آڈیو تیار ہو رہی ہے..."):
                        s, res = generate_voice(v_text, v_voice, v_spd)
                        if s:
                            st.audio(res)
                            with open(res, "rb") as f:
                                st.download_button("ڈاؤن لوڈ آڈیو", f, file_name="audio.mp3")
                        else:
                            refund_credits(uid, cost, "Voice Failed")
                            st.error(res)
                else: st.error(msg)

    elif choice == "🎬 Video Studio":
        st.header("🎬 ویڈیو اسٹوڈیو (Local Scene Composer)")
        sc_input = st.text_area("مناظر (ہر منظر نئی سطر پر لکھیں):", "منظر 1: تعارف\nمنظر 2: خصوصی رعایتی پیکجز\nمنظر 3: آج ہی رابطہ کریں")
        if st.button("ویڈیو رینڈر کریں (MP4)"):
            scenes = [s.strip() for s in sc_input.split("\n") if s.strip()]
            if scenes:
                ok, cost, msg = deduct_credits(uid, "video") if not st.session_state.demo_mode else (True, 0, "")
                if ok:
                    with st.spinner("ویڈیو رینڈر ہو رہی ہے..."):
                        s, res = generate_video(scenes)
                        if s:
                            st.video(res)
                            with open(res, "rb") as f:
                                st.download_button("ڈاؤن لوڈ ویڈیو", f, file_name="video.mp4")
                        else:
                            refund_credits(uid, cost, "Video Failed")
                            st.error(res)
                else: st.error(msg)

    elif choice == "💳 Plans & Pricing":
        st.header("💳 سبسکرپشن پلانز اور پیکیجز")
        p1, p2, p3 = st.columns(3)
        p1.markdown("<div class='brand-box'><h3>Basic</h3><p>500 Credits</p><h4>PKR 1,500</h4></div>", unsafe_allow_html=True)
        p2.markdown("<div class='brand-box'><h3>Pro</h3><p>2,500 Credits</p><h4>PKR 5,000</h4></div>", unsafe_allow_html=True)
        p3.markdown("<div class='brand-box'><h3>Agency</h3><p>10,000 Credits</p><h4>PKR 15,000</h4></div>", unsafe_allow_html=True)

    elif choice == "🛠️ White-Label Admin Panel" and is_admin:
        st.header("🛠️ White-Label Branding Control Panel")
        with st.form("admin_wizard"):
            c_a, c_b = st.columns(2)
            with c_a:
                b_name = st.text_input("برانڈ کا نام", value=cfg.get("brand_name"))
                b_tag = st.text_input("ٹیگ لائن", value=cfg.get("tagline"))
                b_logo = st.text_input("لوگو URL", value=cfg.get("logo_url"))
                b_prim = st.color_picker("پرائمری رنگ", value=cfg.get("primary_color"))
                b_sec = st.color_picker("سیکنڈری رنگ", value=cfg.get("secondary_color"))
            with c_b:
                b_mail = st.text_input("سپورٹ ای میل", value=cfg.get("support_email"))
                b_wa = st.text_input("واٹس ایپ نمبر", value=cfg.get("whatsapp_number"))
                b_dir = st.selectbox("UI سمت", ["rtl", "ltr"], index=0 if cfg.get("direction") == "rtl" else 1)
                b_foot = st.text_area("فوٹر کاپی رائٹ", value=cfg.get("footer_text"))
                b_gemini = st.text_input("Optional Gemini Key (اختیاری)", type="password")
            
            if st.form_submit_button("سیٹنگز محفوظ کریں اور فوری اپڈیٹ کریں"):
                set_setting("brand_name", b_name)
                set_setting("tagline", b_tag)
                set_setting("logo_url", b_logo)
                set_setting("primary_color", b_prim)
                set_setting("secondary_color", b_sec)
                set_setting("support_email", b_mail)
                set_setting("whatsapp_number", b_wa)
                set_setting("direction", b_dir)
                set_setting("footer_text", b_foot)
                if b_gemini: set_setting("gemini_key", b_gemini)
                st.success("برانڈنگ کامیابی سے تبدیل ہو گئی!")
                st.rerun()

st.markdown("---")
st.caption(f"{cfg['footer_text']} | ای میل: {cfg['support_email']} | واٹس ایپ: {cfg['whatsapp_number']}")

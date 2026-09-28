import streamlit as st
import os
from database_saas import init_db, get_db_connection
from config_saas import get_all_settings, set_setting, inject_branding_css
from security_saas import authenticate_user, register_user, deduct_credits, refund_credits
from providers_saas import (
    generate_voice, 
    generate_image, 
    generate_video, 
    generate_chat_response, 
    AVAILABLE_VOICES
)

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
        <img src="{cfg['logo_url']}" width="36" style="vertical-align: middle;" />
        <strong style="font-size: 20px; margin-right: 10px;">{cfg['brand_name']}</strong>
        <p style="margin: 5px 0 0 0; font-size: 12px; opacity: 0.8;">{cfg['tagline']}</p>
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
        st.info("نئے کلائنٹ کے لیے ڈیمو موڈ:")
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

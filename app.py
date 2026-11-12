
import io
import json
import time
import base64
import gc
from PIL import Image, ImageOps
import streamlit as st
import streamlit.components.v1 as components

from core import (
    LANGUAGES, T, PDF_SUPPORT,
    get_active_gemini_key, login_user, format_short_date,
    get_library_with_covers, load_book_content, save_hybrid_book, delete_hybrid_book,
    process_single_image, merge_two_pages, ensure_reading_ready, clean_word_key
)

if PDF_SUPPORT:
    import fitz

st.set_page_config(
    page_title="Fransızca Hikaye Kütüphanesi",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# OTURUM KALICILIĞI (F5 / EKRAN KİLİDİ KORUMASI)
# ==========================================
qp = st.query_params
if "app_lang" not in st.session_state:
    st.session_state.app_lang = qp.get("lang", "tr") if qp.get("lang") in LANGUAGES else "tr"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = bool(qp.get("user", ""))
if "user_email" not in st.session_state:
    st.session_state.user_email = qp.get("user", "")
if "user_role" not in st.session_state:
    st.session_state.user_role = qp.get("role", "family")
if "active_profile" not in st.session_state:
    st.session_state.active_profile = qp.get("profile", "Timuçin")

if "reading_mode" not in st.session_state:
    st.session_state.reading_mode = False
if "editor_mode" not in st.session_state:
    st.session_state.editor_mode = False
if "uploaded_book_pages" not in st.session_state:
    st.session_state.uploaded_book_pages = []
if "current_book_id" not in st.session_state:
    st.session_state.current_book_id = ""
if "current_book_title" not in st.session_state:
    st.session_state.current_book_title = ""
if "editor_pages" not in st.session_state:
    st.session_state.editor_pages = []
if "editor_book_title" not in st.session_state:
    st.session_state.editor_book_title = ""
if "editor_orig_book_id" not in st.session_state:
    st.session_state.editor_orig_book_id = None
if "editor_page_idx" not in st.session_state:
    st.session_state.editor_page_idx = 0

if "profile_progress" not in st.session_state:
    st.session_state.profile_progress = {"Timuçin": {}, "Teoman": {}, "Tolga": {}}
if "profile_completed" not in st.session_state:
    st.session_state.profile_completed = {"Timuçin": set(), "Teoman": set(), "Tolga": set()}
if "profile_words" not in st.session_state:
    st.session_state.profile_words = {"Timuçin": {}, "Teoman": {}, "Tolga": {}}

def sync_query_params():
    if st.session_state.logged_in:
        st.query_params["user"] = st.session_state.user_email
        st.query_params["profile"] = st.session_state.active_profile
        st.query_params["lang"] = st.session_state.app_lang
        st.query_params["role"] = st.session_state.user_role
    else:
        st.query_params.clear()

def collect_book_words_into_bank(pages, profile_name, target_lang):
    bank = st.session_state.profile_words.setdefault(profile_name, {})
    for p in pages:
        for b in p.get("boxes", []):
            fr_w = b.get("text", "").strip()
            ck = b.get("clean") or clean_word_key(fr_w)
            meaning = str(b.get(target_lang) or p.get("dictionary", {}).get(ck, "")).strip()
            if ck and meaning and len(ck) > 1 and meaning != "-":
                bank[fr_w] = meaning

def get_badges_for_profile(profile_name):
    completed_count = len(st.session_state.profile_completed.get(profile_name, set()))
    words_count = len(st.session_state.profile_words.get(profile_name, {}))
    badges = []
    if completed_count >= 1:
        badges.append("🌟 İlk Hikaye Tamamlandı")
    if completed_count >= 3:
        badges.append("🏆 Hikaye Kahramanı (3+ Kitap)")
    if words_count >= 10:
        badges.append("🦉 Kelime Avcısı (10+ Kelime)")
    if words_count >= 30:
        badges.append("👑 Fransızca Ustası (30+ Kelime)")
    if not badges:
        badges.append("🌱 Yeni Kaşif (İlk kitabını oku ve rozet kazan!)")
    return badges

# ==========================================
# 1. GİRİŞ EKRANI (PIN KORUMALI ADMIN SEÇENEĞİ)
# ==========================================
if not st.session_state.logged_in:
    col_e, col_l = st.columns([4, 1.2])
    with col_l:
        sel_lang = st.selectbox(
            "Dil",
            options=list(LANGUAGES.keys()),
            format_func=lambda x: f"{LANGUAGES[x]['flag']} {LANGUAGES[x]['name']}",
            index=list(LANGUAGES.keys()).index(st.session_state.app_lang),
            label_visibility="collapsed"
        )
        if sel_lang != st.session_state.app_lang:
            st.session_state.app_lang = sel_lang
            st.rerun()

    st.markdown(f"<h1 style='text-align:center;color:#1e3a8a;margin-bottom:4px;'>{T('title')}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;color:#64748b;font-size:16px;margin-bottom:24px;'>{T('subtitle')}</p>", unsafe_allow_html=True)

    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        who_choice = st.radio(
            "Kim Okuyor?",
            options=["👦 Timuçin", "👦 Teoman", "👨 Tolga (Yönetici - PIN Gerekli)"],
            horizontal=True
        )
        l_email = st.text_input(T("email_label"), value="tolgakurec@gmail.com", placeholder="ornek@email.com")
        is_admin_try = "Yönetici" in who_choice
        pin_val = ""
        if is_admin_try:
            pin_val = st.text_input(T("pin_label"), type="password", placeholder="****")

        if st.button(T("login_btn"), type="primary", use_container_width=True):
            if l_email and "@" in l_email:
                ok, udata, msg = login_user(l_email, is_admin_attempt=is_admin_try, pin_input=pin_val)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.user_email = udata.get("Email")
                    st.session_state.user_role = udata.get("Role", "family")
                    if "Timuçin" in who_choice:
                        st.session_state.active_profile = "Timuçin"
                    elif "Teoman" in who_choice:
                        st.session_state.active_profile = "Teoman"
                    else:
                        st.session_state.active_profile = "Tolga"
                    sync_query_params()
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning(T("email_warn"))

# ==========================================
# 2. OKUMA MODU (ZEN VIEWER + SES KAYIT + MİNİ QUİZ)
# ==========================================
elif st.session_state.reading_mode:
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"], header, footer { display: none !important; }
            .block-container { padding: 0 !important; margin: 0 !important; max-width: 100vw !important; height: 100vh !important; overflow: hidden !important; background: #06090e !important; }
            iframe { position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; border: none !important; z-index: 1 !important; }
            div[data-testid="stButton"] { position: fixed !important; top: 10px !important; right: 18px !important; z-index: 999999 !important; }
            div[data-testid="stButton"] button {
                background: rgba(15, 23, 42, 0.55) !important; backdrop-filter: blur(14px) !important;
                border: 1px solid rgba(255, 255, 255, 0.2) !important; color: #e2e8f0 !important;
                border-radius: 25px !important; padding: 5px 14px !important; font-weight: 600 !important; font-size: 13px !important;
            }
            div[data-testid="stButton"] button:hover { background: rgba(220, 38, 38, 0.85) !important; color: #fff !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

    if st.button(T("zen_close"), key="btn_exit_zen"):
        prof = st.session_state.active_profile
        bid = st.session_state.current_book_id
        if bid:
            st.session_state.profile_completed.setdefault(prof, set()).add(bid)
        collect_book_words_into_bank(st.session_state.uploaded_book_pages, prof, st.session_state.app_lang)
        st.session_state.reading_mode = False
        st.rerun()

    pages = ensure_reading_ready(st.session_state.uploaded_book_pages, st.session_state.app_lang)
    prof = st.session_state.active_profile
    bid = st.session_state.current_book_id
    start_page_idx = st.session_state.profile_progress.get(prof, {}).get(bid, 0)
    if start_page_idx >= len(pages):
        start_page_idx = 0

    target_flag = LANGUAGES[st.session_state.app_lang]["flag"]
    txt_page = T("zen_page")
    txt_listen = T("zen_listen")
    txt_stop = T("zen_stop")
    txt_trans = T("zen_page_trans")
    txt_loading = T("zen_loading_trans")
    txt_quiz = T("zen_quiz")
    txt_rec = T("zen_rec")
    pages_json = json.dumps(pages)

    HTML_VIEWER = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            * {{ box-sizing: border-box; user-select: none; -webkit-user-select: none; }}
            html, body {{ margin: 0; padding: 0; width: 100vw; height: 100vh; overflow: hidden; background: #06090e; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
            #viewport-wrap {{ position: relative; width: 100vw; height: calc(100vh - 96px); margin-top: 38px; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
            #stage {{ position: relative; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 35px rgba(0,0,0,0.85); border-radius: 8px; background: #000; }}
            #book-img {{ width: 100%; height: 100%; display: block; border-radius: 8px; }}
            #boxes-layer {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }}
            .word-hitbox {{ position: absolute; border-radius: 4px; cursor: pointer; background: rgba(255,255,255,0.01); pointer-events: auto; transition: background 0.12s ease, outline 0.12s ease; }}
            .word-hitbox:hover, .word-hitbox:active {{ background: rgba(254,240,138,0.45); outline: 2px solid #facc15; }}
            .karaoke-lit {{ background: rgba(250,204,21,0.68) !important; outline: 2px solid #eab308 !important; }}
            .glass-pill {{ position: fixed; top: 10px; left: 18px; background: rgba(15,23,42,0.55); backdrop-filter: blur(14px); color: #cbd5e1; font-weight: 600; font-size: 13px; padding: 5px 14px; border-radius: 25px; z-index: 1000; }}
            
            #whisper-card {{
                position: fixed; bottom: 82px; left: 50%; transform: translateX(-50%);
                background: rgba(15,23,42,0.94); backdrop-filter: blur(24px); color: #ffffff;
                padding: 14px 22px; border-radius: 18px; font-size: 15.5px;
                box-shadow: 0 12px 40px rgba(0,0,0,0.75); border: 1px solid rgba(255,255,255,0.2);
                display: none; z-index: 1001; max-width: 660px; width: 92vw; line-height: 1.6;
            }}
            .card-close-btn {{ position: absolute; top: 8px; right: 12px; background: transparent; border: none; color: #94a3b8; font-size: 16px; cursor: pointer; }}
            
            .glass-dock {{
                position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%);
                display: flex; align-items: center; gap: 5px; flex-wrap: nowrap;
                background: rgba(15,23,42,0.65); backdrop-filter: blur(16px);
                padding: 6px 10px; border-radius: 35px; box-shadow: 0 8px 25px rgba(0,0,0,0.6); z-index: 1000;
                max-width: 98vw; overflow-x: auto;
            }}
            .glass-btn {{
                background: rgba(255,255,255,0.08); color: #f1f5f9; border: 1px solid rgba(255,255,255,0.14);
                padding: 7px 12px; border-radius: 25px; font-weight: 600; font-size: 13px; cursor: pointer; white-space: nowrap;
            }}
            .glass-btn.active {{ background: #2563eb !important; border-color: #60a5fa !important; }}
            .glass-btn.rec-on {{ background: #dc2626 !important; border-color: #f87171 !important; animation: pulse 1s infinite; }}
            @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.65; }} 100% {{ opacity: 1; }} }}

            #quiz-modal {{
                position: fixed; inset: 0; background: rgba(6,9,14,0.88); backdrop-filter: blur(16px);
                display: none; align-items: center; justify-content: center; z-index: 2000;
            }}
            .quiz-box {{
                background: #0f172a; border: 1px solid rgba(255,255,255,0.18); border-radius: 22px;
                padding: 24px; max-width: 480px; width: 92vw; color: #f8fafc; text-align: center;
                box-shadow: 0 20px 50px rgba(0,0,0,0.8);
            }}
            .quiz-opt {{
                display: block; width: 100%; margin: 8px 0; padding: 12px; border-radius: 14px;
                background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.15);
                color: #fff; font-size: 15px; font-weight: 600; cursor: pointer;
            }}
            .quiz-opt:hover {{ background: rgba(59,130,246,0.3); }}
        </style>
    </head>
    <body>
        <div id="viewport-wrap"><div id="stage"><img id="book-img" src=""><div id="boxes-layer"></div></div></div>
        <div id="page-counter" class="glass-pill">👦 {prof} • {txt_page} 1 / 1</div>
        
        <div id="whisper-card">
            <button class="card-close-btn" onclick="dismissCard()">✕</button>
            <div id="whisper-body"></div>
        </div>

        <div id="quiz-modal">
            <div class="quiz-box">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <span style="color:#fbbf24;font-weight:bold;">🎯 {txt_quiz}</span>
                    <button onclick="closeQuiz()" style="background:none;border:none;color:#94a3b8;font-size:18px;cursor:pointer;">✕</button>
                </div>
                <div id="quiz-content"></div>
            </div>
        </div>

        <div id="main-dock" class="glass-dock">
            <button id="btn-prev" class="glass-btn" onclick="prevPage()">⬅️</button>
            <button id="btn-speed" class="glass-btn" onclick="cycleSpeed()">⚡ <span id="speed-text">0.85x</span></button>
            <button id="btn-karaoke" class="glass-btn" onclick="toggleKaraoke()">🎤 <span id="k-text">{txt_listen}</span></button>
            <button id="btn-rec" class="glass-btn" onclick="toggleRecord()">🎙️ <span id="rec-text">{txt_rec}</span></button>
            <button id="btn-play-rec" class="glass-btn" style="display:none;" onclick="playMyRecording()">▶️ Dinle</button>
            <button id="btn-trans" class="glass-btn" onclick="toggleTranslation()">{target_flag} <span>{txt_trans}</span></button>
            <button id="btn-quiz" class="glass-btn" onclick="openQuiz()">🎯 <span>{txt_quiz}</span></button>
            <button id="btn-next" class="glass-btn" onclick="nextPage()">➡️</button>
        </div>

        <script>
            const allPages = {pages_json};
            const targetFlag = "{target_flag}";
            const profileName = "{prof}";
            let currentIndex = {start_page_idx}, isPlaying = false, timer = null, wordIndices = [];
            const speeds = [0.7, 0.85, 1.0]; let speedIdx = 1;

            const imgEl = document.getElementById('book-img');
            const stage = document.getElementById('stage');
            const layer = document.getElementById('boxes-layer');
            const wrap = document.getElementById('viewport-wrap');

            let bestFrVoice = null;
            function pickBestFrenchVoice() {{
                const voices = window.speechSynthesis.getVoices() || [];
                const frVoices = voices.filter(v => v.lang && v.lang.toLowerCase().startsWith('fr'));
                bestFrVoice =
                    frVoices.find(v => /denise|henri|google|amelie|thomas|natural|neural/i.test(v.name)) ||
                    frVoices[0] || null;
            }}
            pickBestFrenchVoice();
            if (window.speechSynthesis) {{
                window.speechSynthesis.onvoiceschanged = pickBestFrenchVoice;
            }}

            function speakFrench(text, onBoundaryCb, onEndCb) {{
                if (!window.speechSynthesis) return;
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance(text);
                u.lang = 'fr-FR';
                if (bestFrVoice) u.voice = bestFrVoice;
                u.rate = speeds[speedIdx];
                u.pitch = 1.05;
                if (onBoundaryCb) u.onboundary = onBoundaryCb;
                if (onEndCb) {{ u.onend = onEndCb; u.onerror = onEndCb; }}
                window.speechSynthesis.speak(u);
            }}

            function fitPageToScreen() {{
                if (!imgEl.naturalWidth || !imgEl.naturalHeight) return;
                const availW = wrap.clientWidth * 0.96;
                const availH = wrap.clientHeight * 0.96;
                const scale = Math.min(availW / imgEl.naturalWidth, availH / imgEl.naturalHeight);
                const targetW = Math.round(imgEl.naturalWidth * scale);
                const targetH = Math.round(imgEl.naturalHeight * scale);
                stage.style.width = targetW + 'px'; stage.style.height = targetH + 'px';
                imgEl.style.width = targetW + 'px'; imgEl.style.height = targetH + 'px';
                layer.style.width = targetW + 'px'; layer.style.height = targetH + 'px';
            }}
            window.addEventListener('resize', fitPageToScreen);

            function dismissCard() {{ document.getElementById('whisper-card').style.display = 'none'; clearTimeout(timer); }}
            function cycleSpeed() {{
                speedIdx = (speedIdx + 1) % speeds.length;
                document.getElementById('speed-text').innerText = speeds[speedIdx] + "x";
                if (isPlaying) {{ toggleKaraoke(); setTimeout(toggleKaraoke, 100); }}
            }}

            function loadPage(idx) {{
                if (idx < 0 || idx >= allPages.length) return;
                stopKaraoke(); currentIndex = idx; const page = allPages[idx];
                imgEl.onload = () => {{ fitPageToScreen(); }};
                imgEl.src = "data:image/jpeg;base64," + page.img_b64;
                if (imgEl.complete) {{ fitPageToScreen(); }}

                document.getElementById('page-counter').innerText = `👦 ${{profileName}} • {txt_page} ${{idx + 1}} / ${{allPages.length}}`;
                document.getElementById('btn-prev').disabled = (idx === 0);
                document.getElementById('btn-next').disabled = (idx === allPages.length - 1);
                dismissCard(); layer.innerHTML = ''; wordIndices = []; let charOffset = 0;

                (page.boxes || []).forEach((b, i) => {{
                    wordIndices.push({{ idx: i, start: charOffset, end: charOffset + b.text.length }});
                    charOffset += b.text.length + 1;
                    const d = document.createElement('div'); d.className = 'word-hitbox'; d.id = 'box_' + i;
                    d.style.left = b.left + '%'; d.style.top = b.top + '%'; d.style.width = b.width + '%'; d.style.height = b.height + '%';

                    d.onclick = () => {{
                        clearTimeout(timer);
                        const dict = page.dictionary || {{}};
                        const cleanKey = b.clean || b.text.toLowerCase().trim();
                        let trans = dict[cleanKey] || dict[b.text.toLowerCase().trim()] || '-';
                        if (trans === '-' || !trans) {{
                            let noPunct = b.text.replace(/^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$/g, "").trim().toLowerCase();
                            trans = dict[noPunct] || '-';
                        }}
                        document.getElementById('whisper-body').innerHTML =
                            "<div style='text-align:center;font-size:16px;'>🇫🇷 <b>" + b.text + "</b> &nbsp;➔&nbsp; " + targetFlag + " <b>" + trans + "</b></div>";
                        document.getElementById('whisper-card').style.display = 'block';
                        document.getElementById('whisper-card').dataset.type = 'word';
                        speakFrench(b.text);
                        timer = setTimeout(dismissCard, 4500);
                    }};
                    layer.appendChild(d);
                }});
            }}
            function nextPage() {{ if (currentIndex < allPages.length - 1) loadPage(currentIndex + 1); }}
            function prevPage() {{ if (currentIndex > 0) loadPage(currentIndex - 1); }}

            function toggleTranslation() {{
                clearTimeout(timer);
                const tText = (allPages[currentIndex] && allPages[currentIndex].full_trans) ? allPages[currentIndex].full_trans : "{txt_loading}";
                const card = document.getElementById('whisper-card');
                if (card.style.display === 'block' && card.dataset.type === 'page') {{ dismissCard(); }}
                else {{
                    document.getElementById('whisper-body').innerHTML =
                        `<div style="font-size:13px;font-weight:700;color:#93c5fd;margin-bottom:6px;">📝 {txt_trans} (${{targetFlag}})</div>` +
                        `<div style="font-size:15px;color:#f8fafc;text-align:left;line-height:1.65;max-height:38vh;overflow-y:auto;">${{tText}}</div>`;
                    card.style.display = 'block'; card.dataset.type = 'page';
                }}
            }}

            function toggleKaraoke() {{ if (isPlaying) stopKaraoke(); else playKaraoke(); }}
            function playKaraoke() {{
                isPlaying = true;
                document.getElementById('btn-karaoke').classList.add('active');
                document.getElementById('k-text').innerText = "{txt_stop}";
                const page = allPages[currentIndex];
                const fSent = (page.boxes || []).map(b => b.text).join(' ');
                speakFrench(fSent, (e) => {{
                    if (e.name === 'word') {{
                        const match = wordIndices.find(w => e.charIndex >= w.start && e.charIndex <= w.end);
                        if (match) {{
                            document.querySelectorAll('.word-hitbox').forEach(el => el.classList.remove('karaoke-lit'));
                            const el = document.getElementById('box_' + match.idx);
                            if (el) el.classList.add('karaoke-lit');
                        }}
                    }}
                }}, stopKaraoke);
            }}
            function stopKaraoke() {{
                isPlaying = false;
                if (window.speechSynthesis) window.speechSynthesis.cancel();
                document.getElementById('btn-karaoke').classList.remove('active');
                document.getElementById('k-text').innerText = "{txt_listen}";
                document.querySelectorAll('.word-hitbox').forEach(el => el.classList.remove('karaoke-lit'));
            }}

            let mediaRecorder = null, audioChunks = [], recordedAudioUrl = null, isRecording = false;
            async function toggleRecord() {{
                const btn = document.getElementById('btn-rec');
                const txt = document.getElementById('rec-text');
                if (!isRecording) {{
                    try {{
                        const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                        audioChunks = [];
                        mediaRecorder = new MediaRecorder(stream);
                        mediaRecorder.ondataavailable = e => {{ if (e.data.size > 0) audioChunks.push(e.data); }};
                        mediaRecorder.onstop = () => {{
                            const blob = new Blob(audioChunks, {{ type: 'audio/webm' }});
                            recordedAudioUrl = URL.createObjectURL(blob);
                            document.getElementById('btn-play-rec').style.display = 'inline-block';
                            stream.getTracks().forEach(t => t.stop());
                        }};
                        mediaRecorder.start();
                        isRecording = true;
                        btn.classList.add('rec-on');
                        txt.innerText = "Durdur";
                    }} catch (err) {{
                        alert("Mikrofon izni verilmedi veya cihaz desteklemiyor.");
                    }}
                }} else {{
                    if (mediaRecorder) mediaRecorder.stop();
                    isRecording = false;
                    btn.classList.remove('rec-on');
                    txt.innerText = "{txt_rec}";
                }}
            }}
            function playMyRecording() {{
                if (recordedAudioUrl) {{
                    const a = new Audio(recordedAudioUrl);
                    a.play();
                }}
            }}

            let quizPool = [], qStep = 0, qScore = 0;
            function openQuiz() {{
                const pairs = [];
                const seen = new Set();
                allPages.forEach(p => {{
                    const dict = p.dictionary || {{}};
                    (p.boxes || []).forEach(b => {{
                        const ck = b.clean || b.text.toLowerCase().trim();
                        const tr = dict[ck];
                        if (ck && ck.length > 2 && tr && tr !== '-' && !seen.has(ck)) {{
                            seen.add(ck);
                            pairs.push({{ fr: b.text.replace(/[.,!?]+$/g, ''), ans: tr }});
                        }}
                    }});
                }});
                if (pairs.length < 2) {{
                    alert("Bu kitapta henüz quiz oluşturacak kadar kelime yok.");
                    return;
                }}
                quizPool = pairs.sort(() => 0.5 - Math.random()).slice(0, 4);
                qStep = 0; qScore = 0;
                document.getElementById('quiz-modal').style.display = 'flex';
                renderQuizStep();
            }}
            function closeQuiz() {{ document.getElementById('quiz-modal').style.display = 'none'; }}
            function renderQuizStep() {{
                const box = document.getElementById('quiz-content');
                if (qStep >= quizPool.length) {{
                    box.innerHTML = `<div style="font-size:42px;margin:10px 0;">🌟🏆🌟</div>` +
                        `<h3>Harikasın ${{profileName}}!</h3>` +
                        `<p style="font-size:17px;">Skorun: <b>${{qScore}} / ${{quizPool.length}}</b></p>` +
                        `<button class="quiz-opt" style="background:#2563eb;" onclick="closeQuiz()">Kitaba Dön</button>`;
                    return;
                }}
                const curr = quizPool[qStep];
                const distractors = quizPool.filter((_, idx) => idx !== qStep).map(x => x.ans);
                while (distractors.length < 2) distractors.push("...");
                const opts = [curr.ans, ...distractors.slice(0, 2)].sort(() => 0.5 - Math.random());
                speakFrench(curr.fr);
                let html = `<p style="color:#94a3b8;font-size:13px;">Soru ${{qStep + 1}} / ${{quizPool.length}}</p>` +
                    `<div style="font-size:24px;font-weight:bold;color:#fbbf24;margin:12px 0;cursor:pointer;" onclick="speakFrench('${{curr.fr.replace(/'/g, "\\'")}}')">🔊 ${{curr.fr}}</div>`;
                opts.forEach(o => {{
                    html += `<button class="quiz-opt" onclick="answerQuiz(this, '${{o.replace(/'/g, "\\'")}}', '${{curr.ans.replace(/'/g, "\\'")}}')">${{o}}</button>`;
                }});
                box.innerHTML = html;
            }}
            function answerQuiz(btn, chosen, correct) {{
                if (chosen === correct) {{
                    btn.style.background = "#16a34a";
                    qScore++;
                }} else {{
                    btn.style.background = "#dc2626";
                }}
                setTimeout(() => {{ qStep++; renderQuizStep(); }}, 650);
            }}

            window.addEventListener('keydown', (e) => {{ if (e.key === 'ArrowRight') nextPage(); if (e.key === 'ArrowLeft') prevPage(); }});
            let touchStartX = 0;
            window.addEventListener('touchstart', (e) => {{ touchStartX = e.changedTouches[0].screenX; }}, {{passive: true}});
            window.addEventListener('touchend', (e) => {{ let diff = e.changedTouches[0].screenX - touchStartX; if (diff < -50) nextPage(); if (diff > 50) prevPage(); }}, {{passive: true}});
            loadPage(currentIndex);
        </script>
    </body>
    </html>
    """
    components.html(HTML_VIEWER, height=850, scrolling=False)

# ==========================================
# 3. TEK TABLOLU SADELEŞTİRİLMİŞ DÜZENLEYİCİ
# ==========================================
elif st.session_state.editor_mode:
    st.subheader(f"✏️ Kitap Düzenleyici: {st.session_state.editor_book_title}")

    col_t1, col_t2, col_t3, col_t4 = st.columns([2.5, 1.4, 1.4, 0.9])
    with col_t1:
        st.session_state.editor_book_title = st.text_input("Kitap Adı:", value=st.session_state.editor_book_title, label_visibility="collapsed")
    with col_t2:
        if st.button(T("save_changes"), type="secondary", use_container_width=True):
            with st.spinner("Kaydediliyor..."):
                saved_id, msg = save_hybrid_book(st.session_state.editor_book_title, st.session_state.editor_pages, st.session_state.editor_orig_book_id)
                if saved_id:
                    st.session_state.editor_orig_book_id = saved_id
                    st.success(msg)
                else:
                    st.error(msg)
    with col_t3:
        if st.button(T("save_and_read"), type="primary", use_container_width=True):
            with st.spinner("Kaydediliyor ve açılıyor..."):
                saved_id, msg = save_hybrid_book(st.session_state.editor_book_title, st.session_state.editor_pages, st.session_state.editor_orig_book_id)
                if saved_id:
                    st.session_state.uploaded_book_pages = ensure_reading_ready(st.session_state.editor_pages, st.session_state.app_lang)
                    st.session_state.current_book_id = saved_id
                    st.session_state.current_book_title = st.session_state.editor_book_title
                    st.session_state.editor_mode = False
                    st.session_state.reading_mode = True
                    st.rerun()
                else:
                    st.error(msg)
    with col_t4:
        if st.button(T("exit_editor"), use_container_width=True):
            st.session_state.editor_mode = False
            st.rerun()

    st.divider()
    pages = st.session_state.editor_pages
    total_p = len(pages)

    if total_p > 0:
        with st.expander("⚙️ Toplu İşlemler & Yeni Sayfa Ekle"):
            c_all1, c_all2 = st.columns(2)
            with c_all1:
                if st.button("✨ Tüm Sayfaları Gemini Vision ile Baştan Tara", type="primary", use_container_width=True):
                    p_bar = st.progress(0)
                    for idx, p in enumerate(pages):
                        try:
                            pil_img = Image.open(io.BytesIO(base64.b64decode(p["img_b64"]))).convert("RGB")
                            re_page, _ = process_single_image(pil_img)
                            p["boxes"] = re_page["boxes"]
                        except Exception:
                            pass
                        p_bar.progress((idx + 1) / total_p)
                    st.success("Tüm sayfalar Gemini Vision ile güncellendi!")
                    time.sleep(0.4)
                    st.rerun()
            with c_all2:
                extra_files = st.file_uploader("Kitabın Sonuna Yeni Sayfa Ekle (PNG/JPG):", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="ed_extra_f")
                if extra_files and st.button("➕ Seçilenleri Ekle", use_container_width=True):
                    for ef in extra_files:
                        b_img = ImageOps.exif_transpose(Image.open(ef)).convert("RGB")
                        new_p, _ = process_single_image(b_img)
                        pages.append(new_p)
                    st.session_state.editor_page_idx = len(pages) - 1
                    st.rerun()

    if total_p == 0:
        st.info("Kitapta henüz sayfa yok.")
    else:
        if st.session_state.editor_page_idx >= total_p:
            st.session_state.editor_page_idx = total_p - 1
        p_idx = st.session_state.editor_page_idx
        curr_page = pages[p_idx]

        col_left, col_right = st.columns([1, 1.35])
        with col_left:
            st.markdown(f"### 📄 {T('zen_page')} {p_idx + 1} / {total_p}")
            r1, r2, r3, r4 = st.columns([2, 1, 1, 1])
            with r1:
                new_idx = st.selectbox("Sayfa", options=list(range(total_p)), format_func=lambda i: f"{T('zen_page')} {i + 1}", index=p_idx, label_visibility="collapsed")
                if new_idx != p_idx:
                    st.session_state.editor_page_idx = new_idx
                    st.rerun()
            with r2:
                if st.button("⬆️", disabled=(p_idx == 0), use_container_width=True):
                    pages[p_idx], pages[p_idx - 1] = pages[p_idx - 1], pages[p_idx]
                    st.session_state.editor_page_idx -= 1
                    st.rerun()
            with r3:
                if st.button("⬇️", disabled=(p_idx == total_p - 1), use_container_width=True):
                    pages[p_idx], pages[p_idx + 1] = pages[p_idx + 1], pages[p_idx]
                    st.session_state.editor_page_idx += 1
                    st.rerun()
            with r4:
                if st.button("🗑️", use_container_width=True):
                    pages.pop(p_idx)
                    st.session_state.editor_page_idx = max(0, min(p_idx, len(pages) - 1))
                    st.rerun()

            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button(T("split_page_btn"), use_container_width=True):
                    orig_pil = Image.open(io.BytesIO(base64.b64decode(curr_page["img_b64"]))).convert("RGB")
                    mid_x = orig_pil.width // 2
                    p1, _ = process_single_image(orig_pil.crop((0, 0, mid_x, orig_pil.height)))
                    p2, _ = process_single_image(orig_pil.crop((mid_x, 0, orig_pil.width, orig_pil.height)))
                    pages[p_idx] = p1
                    pages.insert(p_idx + 1, p2)
                    st.rerun()
            with b2:
                if st.button(T("merge_page_btn"), disabled=(p_idx >= total_p - 1), use_container_width=True):
                    pages[p_idx] = merge_two_pages(pages[p_idx], pages[p_idx + 1])
                    pages.pop(p_idx + 1)
                    st.rerun()
            with b3:
                if st.button(T("rescan_page_btn"), type="primary", use_container_width=True):
                    with st.spinner("Gemini Vision okuyor..."):
                        orig_pil = Image.open(io.BytesIO(base64.b64decode(curr_page["img_b64"]))).convert("RGB")
                        re_obj, err = process_single_image(orig_pil)
                        if err:
                            st.error(err)
                        else:
                            curr_page["boxes"] = re_obj["boxes"]
                            st.rerun()

            overlay_divs = "".join([
                f'<div style="position:absolute;left:{b["left"]}%;top:{b["top"]}%;width:{b["width"]}%;height:{b["height"]}%;border:1.5px solid #38bdf8;background:rgba(56,189,248,0.12);pointer-events:none;box-sizing:border-box;border-radius:3px;"></div>'
                for b in curr_page.get("boxes", [])
            ])
            preview_html = (
                f'<div style="text-align:center;background:#0f172a;border-radius:8px;padding:10px;margin-top:10px;display:inline-block;width:100%;">'
                f'<div style="position:relative;display:inline-block;max-width:100%;">'
                f'<img src="data:image/jpeg;base64,{curr_page["img_b64"]}" style="max-width:100%;max-height:460px;object-fit:contain;border-radius:4px;display:block;" />'
                f'{overlay_divs}'
                f'</div></div>'
            )
            st.markdown(preview_html, unsafe_allow_html=True)

        with col_right:
            st.markdown("### 🔤 Sayfa Kelimeleri (Tek Tabloda Düzenle / Sırala / Ekle)")
            table_rows = [
                {
                    "Sıra #": i + 1,
                    "Sil 🗑️": False,
                    "Fransızca": b.get("text", ""),
                    "Türkçe Anlamı": b.get("tr", "")
                }
                for i, b in enumerate(curr_page.get("boxes", []))
            ]
            edited_df = st.data_editor(
                table_rows,
                num_rows="dynamic",
                use_container_width=True,
                height=380,
                key=f"unified_table_{p_idx}_{len(curr_page.get('boxes', []))}",
                column_config={
                    "Sıra #": st.column_config.NumberColumn("Sıra #", min_value=1, step=1, width="small"),
                    "Sil 🗑️": st.column_config.CheckboxColumn("Sil 🗑️", default=False, width="small"),
                    "Fransızca": st.column_config.TextColumn("Fransızca", required=True),
                    "Türkçe Anlamı": st.column_config.TextColumn("Türkçe Anlamı")
                }
            )
            if st.button("🔄 Tablodaki Değişiklikleri Sayfaya Uygula", type="primary", use_container_width=True):
                old_boxes = curr_page.get("boxes", [])
                updated = []
                for i, row in enumerate(edited_df):
                    if row.get("Sil 🗑️", False):
                        continue
                    fr_val = str(row.get("Fransızca") or "").strip()
                    if not fr_val:
                        continue
                    tr_val = str(row.get("Türkçe Anlamı") or "").strip()
                    ord_val = row.get("Sıra #") or (i + 1)
                    if i < len(old_boxes):
                        b_obj = dict(old_boxes[i])
                    else:
                        b_obj = {"id": f"b_{len(updated)}", "left": 10.0, "top": 82.0, "width": 25.0, "height": 7.0}
                    b_obj["text"] = fr_val
                    b_obj["clean"] = clean_word_key(fr_val)
                    if tr_val:
                        b_obj["tr"] = tr_val
                    updated.append((ord_val, b_obj))
                updated.sort(key=lambda x: x[0])
                curr_page["boxes"] = [item[1] for item in updated]
                st.success("Sayfa güncellendi!")
                time.sleep(0.3)
                st.rerun()

# ==========================================
# 4. GÖRSEL KAPAKLI KİTAPLIK VİTRİNİ & PROFİLLER
# ==========================================
else:
    col_u, col_prof, col_lang, col_out = st.columns([2, 2.2, 1.3, 0.9])
    with col_u:
        role_badge = "🔑 Yönetici" if st.session_state.user_role == "admin" else "👨‍👩‍👦 Aile"
        st.markdown(f"**{role_badge}** • `{st.session_state.user_email}`")
    with col_prof:
        prof_opts = ["Timuçin", "Teoman", "Tolga"]
        curr_p_idx = prof_opts.index(st.session_state.active_profile) if st.session_state.active_profile in prof_opts else 0
        new_prof = st.selectbox(
            "Okuyucu Profili:",
            options=prof_opts,
            format_func=lambda x: f"👦 {x}" if x in ["Timuçin", "Teoman"] else f"👨 {x}",
            index=curr_p_idx,
            label_visibility="collapsed"
        )
        if new_prof != st.session_state.active_profile:
            st.session_state.active_profile = new_prof
            sync_query_params()
            st.rerun()
    with col_lang:
        new_lang = st.selectbox(
            "Dil",
            options=list(LANGUAGES.keys()),
            format_func=lambda x: f"{LANGUAGES[x]['flag']} {LANGUAGES[x]['name']}",
            index=list(LANGUAGES.keys()).index(st.session_state.app_lang),
            label_visibility="collapsed"
        )
        if new_lang != st.session_state.app_lang:
            st.session_state.app_lang = new_lang
            sync_query_params()
            st.rerun()
    with col_out:
        if st.button(T("logout"), use_container_width=True):
            st.session_state.logged_in = False
            sync_query_params()
            st.rerun()

    active_prof = st.session_state.active_profile
    badges = get_badges_for_profile(active_prof)
    word_bank = st.session_state.profile_words.get(active_prof, {})

    with st.expander(f"🏅 {active_prof} — {T('badges_title')} & {T('word_bank_title')} ({len(word_bank)} Kelime)", expanded=False):
        st.write(" • ".join(badges))
        if word_bank:
            wb_items = [{"Fransızca": k, "Anlamı": v} for k, v in list(word_bank.items())[-20:]]
            st.dataframe(wb_items, use_container_width=True, hide_index=True)
        else:
            st.caption("Bir kitap okuduğunda öğrendiğin kelimeler otomatik olarak kumbarana eklenecek!")

    col_title, col_ref = st.columns([4.5, 0.8])
    with col_title:
        st.markdown(f"<h2 style='color:#1e3a8a;margin-bottom:0;'>{T('lib_title')}</h2>", unsafe_allow_html=True)
    with col_ref:
        if st.button("🔄 Yenile", use_container_width=True):
            get_library_with_covers.clear()
            st.rerun()

    books, b_err = get_library_with_covers()
    if b_err:
        st.error(f"Veritabanı Hatası: {b_err}")

    if not books:
        st.info(T("empty_lib"))
    else:
        cols = st.columns(3)
        for idx, b in enumerate(books):
            with cols[idx % 3]:
                with st.container(border=True):
                    if b.get("cover_b64"):
                        st.markdown(
                            f'<div style="text-align:center;background:#0f172a;border-radius:8px;padding:6px;margin-bottom:8px;">'
                            f'<img src="data:image/jpeg;base64,{b["cover_b64"]}" style="width:100%;height:220px;object-fit:contain;border-radius:4px;" />'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            '<div style="height:220px;background:#1e293b;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:42px;margin-bottom:8px;">📖</div>',
                            unsafe_allow_html=True
                        )
                    short_d = format_short_date(b.get("date", ""))
                    is_done = b["book_id"] in st.session_state.profile_completed.get(active_prof, set())
                    done_tag = " ✅" if is_done else ""
                    st.markdown(f"**{b['title']}{done_tag}**")
                    st.caption(f"📄 {b['page_count']} sayfa" + (f" • 📅 {short_d}" if short_d else ""))

                    if st.session_state.user_role == "admin":
                        bc1, bc2, bc3 = st.columns([2, 1.4, 1])
                        with bc1:
                            if st.button(T("open_read"), key=f"rd_{b['book_id']}", type="primary", use_container_width=True):
                                with st.spinner(T("ocr_processing")):
                                    b_pages, l_err = load_book_content(b["book_id"])
                                    if b_pages:
                                        st.session_state.uploaded_book_pages = b_pages
                                        st.session_state.current_book_id = b["book_id"]
                                        st.session_state.current_book_title = b["title"]
                                        st.session_state.reading_mode = True
                                        st.rerun()
                                    else:
                                        st.error(l_err)
                        with bc2:
                            if st.button(T("edit_book"), key=f"ed_{b['book_id']}", use_container_width=True):
                                b_pages, l_err = load_book_content(b["book_id"])
                                if b_pages:
                                    st.session_state.editor_pages = b_pages
                                    st.session_state.editor_orig_book_id = b["book_id"]
                                    st.session_state.editor_book_title = b["title"]
                                    st.session_state.editor_page_idx = 0
                                    st.session_state.editor_mode = True
                                    st.rerun()
                        with bc3:
                            if st.button("🗑️", key=f"dl_{b['book_id']}", use_container_width=True):
                                delete_hybrid_book(b["book_id"])
                                st.rerun()
                    else:
                        if st.button(T("open_read"), key=f"rd_{b['book_id']}", type="primary", use_container_width=True):
                            with st.spinner(T("ocr_processing")):
                                b_pages, l_err = load_book_content(b["book_id"])
                                if b_pages:
                                    st.session_state.uploaded_book_pages = b_pages
                                    st.session_state.current_book_id = b["book_id"]
                                    st.session_state.current_book_title = b["title"]
                                    st.session_state.reading_mode = True
                                    st.rerun()
                                else:
                                    st.error(l_err)

    if st.session_state.user_role == "admin":
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander(T("add_tab")):
            book_title_input = st.text_input("Kitabın Adı:", value="Yeni Fransızca Kitap")
            split_spreads = st.checkbox("📖 Çift Sayfaları Otomatik İkiye Böl", value=True)
            upload_mode = st.radio("Kaynak:", ["📄 PDF Belgesi", "📁 Çoklu Fotoğraf", "📸 Kamera"], horizontal=True)

            if upload_mode == "📄 PDF Belgesi":
                uploaded_pdf = st.file_uploader("PDF Dosyası Seçin:", type=["pdf"])
                if uploaded_pdf and PDF_SUPPORT:
                    pdf_doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
                    tot_p = len(pdf_doc)
                    p_range = st.slider("Sayfa Aralığı:", 1, tot_p, (1, tot_p))
                    if st.button("✨ Gemini Vision ile Çözümle & Aktar", type="primary", use_container_width=True):
                        extracted = []
                        prog = st.progress(0)
                        for step, p_no in enumerate(range(p_range[0] - 1, p_range[1])):
                            pix = pdf_doc[p_no].get_pixmap(dpi=130)
                            base_img = Image.open(io.BytesIO(pix.tobytes("jpeg"))).convert("RGB")
                            if split_spreads and (base_img.width / base_img.height) > 1.05:
                                mid = base_img.width // 2
                                p1, _ = process_single_image(base_img.crop((0, 0, mid, base_img.height)))
                                p2, _ = process_single_image(base_img.crop((mid, 0, base_img.width, base_img.height)))
                                extracted.extend([p1, p2])
                            else:
                                p_s, _ = process_single_image(base_img)
                                extracted.append(p_s)
                            del pix, base_img
                            gc.collect()
                            prog.progress((step + 1) / (p_range[1] - p_range[0] + 1))
                        pdf_doc.close()
                        st.session_state.editor_pages = extracted
                        st.session_state.editor_book_title = book_title_input.strip() or "İsimsiz Kitap"
                        st.session_state.editor_orig_book_id = None
                        st.session_state.editor_page_idx = 0
                        st.session_state.editor_mode = True
                        st.rerun()

            elif upload_mode == "📁 Çoklu Fotoğraf":
                upl_files = st.file_uploader("Kitap Sayfaları (PNG/JPG):", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
                if upl_files and st.button("✨ Gemini Vision ile Çözümle & Aktar", type="primary", use_container_width=True):
                    extracted = []
                    prog = st.progress(0)
                    for idx_f, f in enumerate(upl_files):
                        b_img = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
                        if split_spreads and (b_img.width / b_img.height) > 1.05:
                            mid = b_img.width // 2
                            p1, _ = process_single_image(b_img.crop((0, 0, mid, b_img.height)))
                            p2, _ = process_single_image(b_img.crop((mid, 0, b_img.width, b_img.height)))
                            extracted.extend([p1, p2])
                        else:
                            p_s, _ = process_single_image(b_img)
                            extracted.append(p_s)
                        del b_img
                        gc.collect()
                        prog.progress((idx_f + 1) / len(upl_files))
                    st.session_state.editor_pages = extracted
                    st.session_state.editor_book_title = book_title_input.strip() or "İsimsiz Kitap"
                    st.session_state.editor_orig_book_id = None
                    st.session_state.editor_page_idx = 0
                    st.session_state.editor_mode = True
                    st.rerun()

            else:
                cam_pic = st.camera_input("Sayfa Fotoğrafı Çekin")
                if cam_pic and st.button("✨ Gemini Vision ile Çözümle & Aktar", type="primary", use_container_width=True):
                    b_img = ImageOps.exif_transpose(Image.open(cam_pic)).convert("RGB")
                    p_s, _ = process_single_image(b_img)
                    st.session_state.editor_pages = [p_s]
                    st.session_state.editor_book_title = book_title_input.strip() or "İsimsiz Kitap"
                    st.session_state.editor_orig_book_id = None
                    st.session_state.editor_page_idx = 0
                    st.session_state.editor_mode = True
                    st.rerun()

    st.markdown(
        f"<div style='text-align:center;color:#94a3b8;font-size:13px;margin-top:32px;'>✍️ {T('created_by')} • Sol üst menüden <b>Atatürk ve Miti</b> anı köşesine ulaşabilirsiniz.</div>",
        unsafe_allow_html=True
    )

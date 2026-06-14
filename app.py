"""
IIUI Survey Bot — Streamlit Frontend
Run with: streamlit run app.py
"""

import queue
import logging
import threading
import time
import os
from pathlib import Path

import streamlit as st

# ── Page config (MUST be first Streamlit call) ─────────────────────────────────
st.set_page_config(
    page_title="IIUI Survey Bot",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Hide default Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* ── Background ── */
.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    min-height: 100vh;
}

/* ── Main card ── */
.main-card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 24px;
    padding: 2.5rem 2.5rem 2rem;
    margin: 1.5rem auto;
    max-width: 680px;
    box-shadow: 0 25px 60px rgba(0,0,0,0.45);
}

/* ── Header ── */
.hero-title {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-align: center;
    margin: 0;
}
.hero-sub {
    color: rgba(255,255,255,0.55);
    text-align: center;
    font-size: 0.92rem;
    margin-top: 0.35rem;
    margin-bottom: 2rem;
}

/* ── Input labels ── */
label, .stTextInput label, .stSelectbox label, .stTextArea label {
    color: rgba(255,255,255,0.80) !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
}

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 12px !important;
    color: #fff !important;
    padding: 0.65rem 1rem !important;
    font-size: 0.95rem !important;
    transition: border 0.2s ease;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #a78bfa !important;
    box-shadow: 0 0 0 3px rgba(167,139,250,0.18) !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 12px !important;
    color: #fff !important;
}

/* ── Primary button ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 0.75rem 2rem !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    width: 100% !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    box-shadow: 0 6px 20px rgba(124,58,237,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 28px rgba(124,58,237,0.50) !important;
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0) !important;
}

/* ── Log box ── */
.log-box {
    background: rgba(0,0,0,0.45);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    font-family: 'Courier New', monospace;
    font-size: 0.78rem;
    color: #a3e635;
    max-height: 320px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
    line-height: 1.6;
}

/* ── Stat cards ── */
.stat-row {
    display: flex;
    gap: 1rem;
    margin-top: 1.2rem;
}
.stat-card {
    flex: 1;
    background: rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 1rem;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.10);
}
.stat-card .stat-num {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
}
.stat-card .stat-label {
    font-size: 0.75rem;
    color: rgba(255,255,255,0.55);
    margin-top: 0.3rem;
}
.green  { color: #34d399; }
.red    { color: #f87171; }
.yellow { color: #fbbf24; }
.blue   { color: #60a5fa; }

/* ── Divider ── */
.custom-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.08);
    margin: 1.5rem 0;
}

/* ── Badge ── */
.status-badge {
    display: inline-block;
    padding: 0.25rem 0.8rem;
    border-radius: 99px;
    font-size: 0.78rem;
    font-weight: 600;
}
.badge-running { background: rgba(251,191,36,0.15); color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); }
.badge-success { background: rgba(52,211,153,0.15); color: #34d399; border: 1px solid rgba(52,211,153,0.3); }
.badge-error   { background: rgba(248,113,113,0.15); color: #f87171; border: 1px solid rgba(248,113,113,0.3); }
</style>
""", unsafe_allow_html=True)


# ── Queue-based logging handler ────────────────────────────────────────────────
class QueueLogHandler(logging.Handler):
    def __init__(self, q: queue.Queue):
        super().__init__()
        self.q = q
        self.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record):
        try:
            self.q.put(self.format(record))
        except Exception:
            pass


# ── Bot runner (runs in a background thread) ──────────────────────────────────
def run_bot_thread(reg_no: str, password: str, rating: str, comment: str,
                   log_q: queue.Queue, result: dict):
    from iiui_survey_bot import IIUISurveyBot

    handler = QueueLogHandler(log_q)
    root = logging.getLogger()
    root.addHandler(handler)
    bot = None

    try:
        log_q.put("🚀  Launching browser (headless)…")
        bot = IIUISurveyBot(reg_no=reg_no, password=password, headless=True)

        log_q.put("🔐  Logging in…")
        if not bot.login():
            log_q.put("❌  Login failed. Check your credentials.")
            result["status"] = "error"
            result["message"] = "Login failed. Please verify your registration number and password."
            return

        log_q.put("✅  Login successful! Scanning for pending surveys…")
        summary = bot.complete_all_surveys(rating=rating, comment=comment)

        result["status"]  = "success"
        result["summary"] = summary

    except Exception as exc:
        log_q.put(f"❌  Fatal error: {exc}")
        result["status"]  = "error"
        result["message"] = str(exc)

    finally:
        if bot:
            bot.close()
        root.removeHandler(handler)
        log_q.put(None)  # Sentinel — signals the UI that the thread is done


# ── Session-state init ─────────────────────────────────────────────────────────
for key, default in {
    "running":  False,
    "log_lines": [],
    "result":   {},
    "thread":   None,
    "log_q":    None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Drain log queue into session state ────────────────────────────────────────
def drain_queue():
    if st.session_state.log_q is None:
        return
    while True:
        try:
            msg = st.session_state.log_q.get_nowait()
            if msg is None:          # Sentinel — bot finished
                st.session_state.running = False
            else:
                st.session_state.log_lines.append(msg)
        except queue.Empty:
            break


# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="main-card">', unsafe_allow_html=True)

# Header
st.markdown('<h1 class="hero-title">🤖 IIUI Survey Bot</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">Enter your ERP credentials — the bot handles everything else automatically.</p>',
    unsafe_allow_html=True
)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# ── Form ───────────────────────────────────────────────────────────────────────
is_running = st.session_state.running

reg_no = st.text_input(
    "📋  Registration Number",
    placeholder="e.g. 5111124029",
    disabled=is_running,
    key="reg_input",
)

password = st.text_input(
    "🔒  Password",
    type="password",
    placeholder="Your ERP portal password",
    disabled=is_running,
    key="pass_input",
)

rating = st.selectbox(
    "⭐  Rating for all questions",
    options=["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"],
    disabled=is_running,
    key="rating_input",
)

comment = st.text_area(
    "💬  Comment (filled in all text fields)",
    value="I filled this survey using my personal Agent, Thank you",
    height=80,
    disabled=is_running,
    key="comment_input",
)

st.markdown("<br>", unsafe_allow_html=True)

# ── Start button ───────────────────────────────────────────────────────────────
if not is_running:
    if st.button("🚀  Start Survey Bot", type="primary", key="start_btn"):
        if not reg_no.strip():
            st.error("Please enter your registration number.")
        elif not password.strip():
            st.error("Please enter your password.")
        else:
            # Reset state
            st.session_state.log_lines = []
            st.session_state.result    = {}
            st.session_state.running   = True
            st.session_state.log_q     = queue.Queue()

            result_container = {}
            st.session_state.result_ref = result_container

            t = threading.Thread(
                target=run_bot_thread,
                args=(
                    reg_no.strip(),
                    password.strip(),
                    rating,
                    comment.strip(),
                    st.session_state.log_q,
                    result_container,
                ),
                daemon=True,
            )
            t.start()
            st.session_state.thread = t
            st.rerun()
else:
    if st.button("⛔  Stop", type="primary", key="stop_btn"):
        st.session_state.running = False
        st.rerun()

# ── Progress area ──────────────────────────────────────────────────────────────
if is_running or st.session_state.log_lines:
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Drain new log lines
    drain_queue()

    # Status badge
    if st.session_state.running:
        st.markdown(
            '<span class="status-badge badge-running">⏳ Running…</span>',
            unsafe_allow_html=True
        )
    elif st.session_state.result.get("status") == "success":
        st.markdown(
            '<span class="status-badge badge-success">✅ Completed</span>',
            unsafe_allow_html=True
        )
    elif st.session_state.result.get("status") == "error":
        st.markdown(
            '<span class="status-badge badge-error">❌ Error</span>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Live log
    log_text = "\n".join(st.session_state.log_lines[-120:])  # keep last 120 lines
    st.markdown(f'<div class="log-box">{log_text}</div>', unsafe_allow_html=True)

    # Auto-refresh while running
    if st.session_state.running:
        time.sleep(0.8)
        st.rerun()

# ── Result summary ─────────────────────────────────────────────────────────────
result = getattr(st.session_state, "result_ref", {}) if not st.session_state.running else {}

# Sync result dict from thread result_ref when done
if not st.session_state.running and hasattr(st.session_state, "result_ref"):
    ref = st.session_state.result_ref
    if ref and not st.session_state.result:
        st.session_state.result = ref

final = st.session_state.result
if not st.session_state.running and final:
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    if final.get("status") == "success":
        s = final.get("summary", {})
        completed = s.get("completed", 0)
        failed    = s.get("failed", 0)
        skipped   = s.get("skipped", 0)

        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-card">
                <div class="stat-num green">{completed}</div>
                <div class="stat-label">Surveys Submitted</div>
            </div>
            <div class="stat-card">
                <div class="stat-num yellow">{skipped}</div>
                <div class="stat-label">Skipped</div>
            </div>
            <div class="stat-card">
                <div class="stat-num red">{failed}</div>
                <div class="stat-label">Failed</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if completed == 0 and failed == 0:
            st.info("ℹ️  All surveys were already submitted — nothing new to fill!")

    elif final.get("status") == "error":
        st.error(f"❌  {final.get('message', 'An unknown error occurred.')}")

# ── Debug screenshots ──────────────────────────────────────────────────────────
ss_dir = Path("debug_screenshots")
screenshots = sorted(ss_dir.glob("*.png"), reverse=True)[:5] if ss_dir.exists() else []

if screenshots and not st.session_state.running:
    with st.expander("📸 Debug Screenshots (latest 5)"):
        for img in screenshots:
            st.image(str(img), caption=img.name, use_container_width=True)

# ── Reset button ───────────────────────────────────────────────────────────────
if not st.session_state.running and final:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄  Run Again", key="reset_btn"):
        st.session_state.log_lines = []
        st.session_state.result    = {}
        if hasattr(st.session_state, "result_ref"):
            del st.session_state.result_ref
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown(
    "<p style='text-align:center; color:rgba(255,255,255,0.2); font-size:0.75rem; "
    "margin-top:1.5rem;'>IIUI Survey Bot • Educational Use Only</p>",
    unsafe_allow_html=True
)

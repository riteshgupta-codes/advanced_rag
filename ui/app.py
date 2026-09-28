import os
import html
import time
import uuid
import json
from datetime import datetime

import requests
import streamlit as st
import logfire
from dotenv import load_dotenv

# =====================================================================
#  ENVIRONMENT
# =====================================================================
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=env_path)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

# =====================================================================
#  LOGFIRE (safe wrappers)
# =====================================================================
class _SafeSpan:
    def __init__(self, name, kwargs):
        self.name, self.kwargs, self._cm = name, kwargs, None
    def __enter__(self):
        try:
            self._cm = logfire.span(self.name, **self.kwargs)
            self._cm.__enter__()
        except Exception:
            self._cm = None
        return self
    def __exit__(self, *exc):
        if self._cm:
            try:
                return self._cm.__exit__(*exc)
            except Exception:
                return False
        return False

def span(name, **kwargs):
    return _SafeSpan(name, kwargs)

def log_event(level, msg, **kwargs):
    try:
        getattr(logfire, level)(msg, **kwargs)
    except Exception:
        pass

try:
    _token = os.getenv("LOGFIRE_TOKEN")
    logfire.configure(token=_token)
    LOGFIRE_OK = True
    LOGFIRE_STATUS = "Connected"
except Exception as e:
    LOGFIRE_OK = False
    LOGFIRE_STATUS = f"Standby ({type(e).__name__})"

# =====================================================================
#  PAGE CONFIG
# =====================================================================
st.set_page_config(
    page_title="Advanced Agentic RAG",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

AI_AVATAR = "🧬"
USER_AVATAR = "👤"

# =====================================================================
#  CSS — fixed sidebar, no display/transform/visibility hacks
# =====================================================================
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root{
  --accent:#38bdf8;
  --accent-2:#a78bfa;
  --accent-3:#34d399;
  --ink:#e6edf3;
  --muted:#8b9bb4;
  --stroke:rgba(255,255,255,.08);
}

html, body, [class*="css"], .stApp, button, input, textarea, select{
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif !important;
}

/* Animated backdrop */
.stApp{
  background-image:
    radial-gradient(900px 520px at 12% -8%, rgba(56,189,248,.20), transparent 62%),
    radial-gradient(820px 520px at 92% 2%, rgba(167,139,250,.18), transparent 58%),
    radial-gradient(760px 620px at 50% 112%, rgba(52,211,153,.12), transparent 62%),
    linear-gradient(120deg,#06090f,#0c1322,#080d16,#06090f);
  background-size:100% 100%,100% 100%,100% 100%,300% 300%;
  background-attachment:fixed;
  animation:bgDrift 28s ease-in-out infinite;
  color:var(--ink);
}
@keyframes bgDrift{
  0%,100%{ background-position:0 0, 0 0, 0 0, 0% 50%; }
  50%    { background-position:0 0, 0 0, 0 0, 100% 50%; }
}

[data-testid="stHeader"]{ background:transparent; }

/* Hide only the deploy button + main menu + footer.
   DO NOT hide [data-testid="stToolbar"] — it contains the sidebar toggle. */
#MainMenu, footer, [data-testid="stAppDeployButton"]{ visibility:hidden; }
[data-testid="stToolbar"]{ background:transparent !important; }

@keyframes fadeUp{ from{opacity:0; transform:translateY(16px);} to{opacity:1; transform:none;} }
@keyframes slideIn{ from{opacity:0; transform:translateX(-12px);} to{opacity:1; transform:none;} }
@keyframes shimmer{ 0%{background-position:200% 0;} 100%{background-position:-200% 0;} }
@keyframes orbPulse{ 0%,100%{transform:scale(.65); opacity:.45;} 50%{transform:scale(1.15); opacity:1;} }
@keyframes pip{ 0%,100%{opacity:1; transform:scale(1);} 50%{opacity:.3; transform:scale(.7);} }
@keyframes pulseWidth{ 0%,100%{width:90px; opacity:.45;} 50%{width:230px; opacity:1;} }
@keyframes floatY{ 0%,100%{transform:translateY(0);} 50%{transform:translateY(-5px);} }

/* Hero */
.hero{ text-align:center; padding:6px 0 4px; animation:fadeUp .8s cubic-bezier(.22,1,.36,1) both; }
.hero .badge-top{
  display:inline-flex; align-items:center; gap:8px;
  padding:5px 14px; border-radius:999px; margin-bottom:12px;
  font-size:.7rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase;
  color:#7dd3fc; border:1px solid rgba(56,189,248,.35);
  background:rgba(56,189,248,.06);
}
.hero h1{
  margin:0; font-size:3rem; font-weight:800; letter-spacing:-.035em; line-height:1.1;
  background:linear-gradient(90deg,#38bdf8,#a78bfa,#34d399,#38bdf8);
  background-size:300% 100%;
  -webkit-background-clip:text; background-clip:text;
  -webkit-text-fill-color:transparent; color:transparent;
  animation:bgDrift 9s linear infinite;
}
.hero h1 .accent{ animation:floatY 3.4s ease-in-out infinite; display:inline-block; }
.hero p{ margin:10px 0 0; color:var(--muted); font-size:.95rem; }
.hero .rule{
  height:2px; margin:18px auto 4px; border-radius:2px;
  background:linear-gradient(90deg,transparent,var(--accent),transparent);
  animation:pulseWidth 3.6s ease-in-out infinite;
}

/* Chat messages */
[data-testid="stChatMessage"]{
  animation:fadeUp .45s cubic-bezier(.22,1,.36,1) both;
  border:1px solid var(--stroke);
  border-radius:18px;
  background:rgba(255,255,255,.035);
  padding:16px 18px;
  margin-bottom:12px;
  box-shadow:0 8px 30px rgba(0,0,0,.25);
  transition:border-color .25s ease, box-shadow .25s ease, transform .25s ease;
}
[data-testid="stChatMessage"]:hover{
  border-color:rgba(56,189,248,.35);
  box-shadow:0 12px 38px rgba(56,189,248,.12);
  transform:translateY(-1px);
}
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"],
[data-testid="stChatMessageAvatarCustom"]{
  border-radius:50%;
  box-shadow:0 0 0 1px rgba(255,255,255,.08), 0 0 18px rgba(56,189,248,.35);
}
.compact [data-testid="stChatMessage"]{ padding:10px 14px; margin-bottom:8px; }

/* Thinking loader */
.thinking{
  display:flex; align-items:center; gap:12px;
  padding:14px 16px; border-radius:14px;
  border:1px solid rgba(56,189,248,.18);
  background:linear-gradient(90deg,rgba(56,189,248,.08),rgba(167,139,250,.10),rgba(56,189,248,.08));
  background-size:200% 100%;
  animation:shimmer 2.4s linear infinite;
}
.thinking .orb{
  width:12px; height:12px; border-radius:50%;
  background:radial-gradient(circle at 30% 30%,#7dd3fc,#0ea5e9);
  animation:orbPulse 1.2s ease-in-out infinite;
}
.thinking .orb:nth-child(2){
  animation-delay:.16s;
  background:radial-gradient(circle at 30% 30%,#c4b5fd,#8b5cf6);
}
.thinking .orb:nth-child(3){
  animation-delay:.32s;
  background:radial-gradient(circle at 30% 30%,#6ee7b7,#10b981);
}
.thinking .txt{ color:var(--muted); font-size:.9rem; }

/* Steps */
.steps{ display:flex; flex-direction:column; gap:8px; margin:6px 0 2px; }
.step{
  display:flex; align-items:flex-start; gap:10px;
  font-size:.88rem; color:#b9c6d8;
  padding:8px 12px; border-radius:10px;
  background:rgba(255,255,255,.03);
  border-left:2px solid rgba(56,189,248,.55);
  animation:slideIn .45s cubic-bezier(.22,1,.36,1) both;
}
.step .bullet{ color:var(--accent); flex:0 0 auto; }

/* Badges */
.badge{
  display:inline-flex; align-items:center; gap:7px;
  padding:5px 11px; border-radius:999px;
  font-size:.7rem; font-weight:600; letter-spacing:.05em; text-transform:uppercase;
  border:1px solid var(--stroke); background:rgba(255,255,255,.04); color:var(--muted);
  margin:3px 0; white-space:nowrap;
}
.badge.ok  { border-color:rgba(52,211,153,.40); color:#6ee7b7; background:rgba(52,211,153,.08); }
.badge.warn{ border-color:rgba(251,191,36,.40); color:#fcd34d; background:rgba(251,191,36,.08); }
.badge.err { border-color:rgba(248,113,113,.40); color:#fca5a5; background:rgba(248,113,113,.08); }
.badge .pip{ width:7px; height:7px; border-radius:50%; background:currentColor; animation:pip 1.8s ease-in-out infinite; }

/* Sidebar: ONLY styling — no display/transform/visibility overrides */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,rgba(12,18,30,.98),rgba(7,10,16,.99)) !important;
  border-right:1px solid rgba(255,255,255,.06) !important;
}
[data-testid="stSidebar"] > div:first-child{ padding-top:1rem; }

.side-brand{ display:flex; align-items:center; gap:12px; padding:4px 0 10px; }
.side-logo{
  width:46px; height:46px; border-radius:14px; flex:0 0 auto;
  display:flex; align-items:center; justify-content:center;
  font-size:1.4rem;
  background:linear-gradient(135deg,rgba(56,189,248,.30),rgba(167,139,250,.30));
  border:1px solid rgba(56,189,248,.30);
  box-shadow:0 0 22px rgba(56,189,248,.25);
  animation:floatY 4s ease-in-out infinite;
}
.side-title{
  font-size:1.05rem; font-weight:800; letter-spacing:-.02em; margin:0; line-height:1.15;
  background:linear-gradient(90deg,#38bdf8,#a78bfa);
  -webkit-background-clip:text; background-clip:text;
  -webkit-text-fill-color:transparent;
}
.side-sub{ color:var(--muted); font-size:.68rem; letter-spacing:.08em; text-transform:uppercase; margin-top:2px; }

.side-section{
  font-size:.68rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
  color:var(--muted); margin:16px 0 8px;
  display:flex; align-items:center; gap:8px;
}
.side-section::after{
  content:""; flex:1; height:1px;
  background:linear-gradient(90deg,rgba(56,189,248,.35),transparent);
}

.metric-card{
  border:1px solid var(--stroke); border-radius:14px; padding:10px 12px;
  background:rgba(255,255,255,.03); text-align:center;
}
.metric-card .v{ font-size:1.05rem; font-weight:700; color:var(--ink); }
.metric-card .k{ font-size:.62rem; color:var(--muted); text-transform:uppercase; letter-spacing:.07em; }

/* Buttons */
.stButton > button, .stDownloadButton > button{
  width:100%;
  border-radius:14px !important;
  border:1px solid rgba(56,189,248,.30) !important;
  background:linear-gradient(135deg,rgba(56,189,248,.14),rgba(167,139,250,.14)) !important;
  color:var(--ink) !important;
  font-weight:600 !important;
  padding:.5rem 1rem !important;
  transition:transform .2s ease, box-shadow .2s ease, border-color .2s ease !important;
}
.stButton > button:hover, .stDownloadButton > button:hover{
  transform:translateY(-2px);
  border-color:rgba(56,189,248,.85) !important;
  box-shadow:0 10px 26px rgba(56,189,248,.25);
}
.danger-btn .stButton > button{
  border-color:rgba(248,113,113,.35) !important;
  background:linear-gradient(135deg,rgba(248,113,113,.15),rgba(239,68,68,.10)) !important;
}
.danger-btn .stButton > button:hover{
  border-color:rgba(248,113,113,.85) !important;
  box-shadow:0 10px 26px rgba(248,113,113,.25);
}
.tiny-btn .stButton > button{ padding:.25rem .5rem !important; font-size:.78rem !important; }

/* Chat input */
[data-testid="stChatInput"], .stChatInput{
  border-radius:18px !important;
  border:1px solid rgba(56,189,248,.28) !important;
  background:rgba(10,15,24,.92) !important;
}
[data-testid="stChatInput"]:focus-within, .stChatInput:focus-within{
  border-color:rgba(56,189,248,.75) !important;
  box-shadow:0 0 0 4px rgba(56,189,248,.14);
}

/* Expanders */
details{
  border-radius:14px !important;
  border:1px solid var(--stroke) !important;
  background:rgba(255,255,255,.03) !important;
  overflow:hidden;
}
details:hover{ border-color:rgba(56,189,248,.30) !important; }
details summary{ font-weight:600; }
details summary:hover{ color:var(--accent) !important; }

/* Empty state */
.empty-state{
  text-align:center; padding:38px 16px;
  border:1px dashed rgba(56,189,248,.25); border-radius:20px;
  background:rgba(56,189,248,.03);
  animation:fadeUp .7s ease both;
}
.empty-state .ico{ font-size:2.4rem; animation:orbPulse 3s ease-in-out infinite; display:inline-block; }
.empty-state h3{ margin:12px 0 6px; font-weight:700; color:var(--ink); }
.empty-state p{ margin:0; color:var(--muted); font-size:.9rem; }

/* Thread chip */
.thread-chip{
  display:flex; align-items:center; gap:8px;
  padding:8px 10px; border-radius:10px;
  border:1px solid rgba(255,255,255,.06);
  background:rgba(255,255,255,.02);
  font-size:.8rem; color:#c8d3e2;
  margin-bottom:6px;
}
.thread-chip.active{
  border-color:rgba(56,189,248,.55);
  background:rgba(56,189,248,.08);
  box-shadow:0 0 0 1px rgba(56,189,248,.15) inset;
}

/* Scrollbar */
::-webkit-scrollbar{ width:9px; height:9px; }
::-webkit-scrollbar-track{ background:transparent; }
::-webkit-scrollbar-thumb{ background:rgba(56,189,248,.25); border-radius:8px; }
::-webkit-scrollbar-thumb:hover{ background:rgba(56,189,248,.45); }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

THINKING_HTML = """
<div class="thinking">
  <span class="orb"></span><span class="orb"></span><span class="orb"></span>
  <span class="txt">Retrieving context &amp; reasoning over your documents…</span>
</div>
"""

# =====================================================================
#  SESSION STATE
# =====================================================================
def _new_thread_id():
    return str(uuid.uuid4())

defaults = {
    "session_id": _new_thread_id(),
    "started_at": time.time(),
    "messages": [],
    "stream_effect": True,
    "request_timeout": 60,
    "top_k": 4,
    "temperature": 0.2,
    "model": "gpt-4o-mini",
    "agent_mode": "Balanced",
    "system_prompt": "",
    "tools_enabled": {"web_search": False, "calculator": False, "code": False},
    "auto_scroll": True,
    "compact_view": False,
    "latencies": [],
    "threads": {},            # thread_id -> {title, created, messages, latencies}
    "feedback": {},           # message_index -> "up"|"down"
    "search_query": "",
    "uploaded_files": [],
    "token_stats": {"prompt": 0, "completion": 0, "total": 0},
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Register current thread
st.session_state.threads.setdefault(st.session_state.session_id, {
    "title": "New chat",
    "created": time.time(),
    "messages": [],
    "latencies": [],
})

log_event("info", f"✨ Session ready: {st.session_state.session_id}")

# =====================================================================
#  HELPERS
# =====================================================================
@st.cache_data(ttl=20, show_spinner=False)
def check_backend(url: str):
    try:
        r = requests.get(url, timeout=2.5)
        return (r.status_code < 500), f"Online · {r.status_code}"
    except Exception:
        return False, "Offline"


def call_backend(query, thread_id, timeout, top_k, temperature,
                 model=None, system_prompt=None, tools=None, mode=None):
    payload = {
        "q": query,
        "thread_id": thread_id,
        "top_k": top_k,
        "temperature": temperature,
    }
    if model:        payload["model"] = model
    if system_prompt: payload["system_prompt"] = system_prompt
    if tools:        payload["tools"] = [k for k, v in tools.items() if v]
    if mode:         payload["mode"] = mode.lower()

    resp = requests.post(f"{BACKEND_URL}/query", json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def upload_document(file, thread_id):
    try:
        files = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
        data = {"thread_id": thread_id}
        resp = requests.post(f"{BACKEND_URL}/ingest", files=files, data=data, timeout=180)
        if resp.status_code == 404:
            return False, "Endpoint /ingest not found on backend"
        resp.raise_for_status()
        try:
            return True, resp.json()
        except Exception:
            return True, {"status": "ok"}
    except Exception as e:
        return False, str(e)


def render_steps(steps) -> str:
    rows = "".join(
        f'<div class="step" style="animation-delay:{i * 0.08:.2f}s">'
        f'<span class="bullet">⚙️</span><span>{html.escape(str(s))}</span></div>'
        for i, s in enumerate(steps)
    )
    return f'<div class="steps">{rows}</div>'


def typewriter(placeholder, text, base_delay=0.008, min_frames=60, max_frames=260):
    n = len(text)
    if n == 0:
        placeholder.markdown("")
        return
    frames = max(min_frames, min(max_frames, n))
    chunk = max(1, n // frames)
    i = 0
    while i < n:
        i += chunk
        placeholder.markdown(text[:i] + " ▌")
        time.sleep(base_delay)
    placeholder.markdown(text)


def render_sources(sources):
    with st.expander(f"📄 Retrieved context · {len(sources)} chunk(s)"):
        for i, src in enumerate(sources):
            head = " ".join(str(src).split())[:90]
            with st.expander(f"Chunk {i + 1} · {head}…"):
                st.info(src)


def latency_stats(vals):
    if not vals:
        return None
    return {
        "avg": sum(vals) / len(vals),
        "min": min(vals),
        "max": max(vals),
        "last": vals[-1],
        "n": len(vals),
    }


def switch_thread(tid):
    st.session_state.session_id = tid
    t = st.session_state.threads.setdefault(tid, {
        "title": "New chat", "created": time.time(), "messages": [], "latencies": [],
    })
    st.session_state.messages = t["messages"]
    st.session_state.latencies = t["latencies"]


def persist_current():
    tid = st.session_state.session_id
    t = st.session_state.threads.setdefault(tid, {
        "title": "New chat", "created": time.time(), "messages": [], "latencies": [],
    })
    t["messages"] = st.session_state.messages
    t["latencies"] = st.session_state.latencies
    # auto-title from first user message
    if t["title"] == "New chat" and st.session_state.messages:
        first_user = next((m for m in st.session_state.messages if m["role"] == "user"), None)
        if first_user:
            t["title"] = (" ".join(first_user["content"].split()))[:34] + ("…" if len(first_user["content"]) > 34 else "")


# =====================================================================
#  SIDEBAR  (st.sidebar — no display hacks, always visible)
# =====================================================================
sb = st.sidebar

sb.markdown(
    """
    <div class="side-brand">
      <div class="side-logo">🧬</div>
      <div>
        <div class="side-title">Advanced<br>Agentic RAG</div>
        <div class="side-sub">Control Panel</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- System status ----
sb.markdown('<div class="side-section">System Status</div>', unsafe_allow_html=True)

lf_cls = "ok" if LOGFIRE_OK else "warn"
sb.markdown(
    f'<span class="badge {lf_cls}"><span class="pip"></span>Logfire · {html.escape(LOGFIRE_STATUS)}</span>',
    unsafe_allow_html=True,
)

be_ok, be_msg = check_backend(BACKEND_URL)
be_cls = "ok" if be_ok else "err"
sb.markdown(
    f'<span class="badge {be_cls}"><span class="pip"></span>Backend · {html.escape(be_msg)}</span>',
    unsafe_allow_html=True,
)

ca, cb = sb.columns(2)
with ca:
    if st.button("🔄 Refresh", key="refresh_status", width="stretch"):
        check_backend.clear()
        st.rerun()
with cb:
    if st.button("🔌 Ping", key="ping_api", width="stretch"):
        try:
            r = requests.get(BACKEND_URL, timeout=3)
            st.toast(f"✅ API responded {r.status_code}", icon="🟢")
        except Exception as e:
            st.toast(f"❌ {type(e).__name__}", icon="🔴")

sb.caption(f"`{BACKEND_URL}`")

# ---- Threads ----
sb.markdown('<div class="side-section">Threads</div>', unsafe_allow_html=True)

if sb.button("➕ New chat", key="new_thread", width="stretch"):
    persist_current()
    new_id = _new_thread_id()
    st.session_state.threads[new_id] = {
        "title": "New chat", "created": time.time(), "messages": [], "latencies": [],
    }
    switch_thread(new_id)
    st.rerun()

# list threads, newest first
_sorted = sorted(st.session_state.threads.items(), key=lambda kv: kv[1]["created"], reverse=True)
for tid, t in _sorted[:8]:
    active = tid == st.session_state.session_id
    dot = "🟢" if active else "⚪"
    count = len(t.get("messages", []))
    label = f"{dot}  {t['title']}  ·  {count}"
    if sb.button(label, key=f"thr_{tid}", width="stretch"):
        if not active:
            persist_current()
            switch_thread(tid)
            st.rerun()

if len(_sorted) > 8:
    sb.caption(f"…and {len(_sorted) - 8} older thread(s)")

# ---- Knowledge base upload ----
sb.markdown('<div class="side-section">Knowledge Base</div>', unsafe_allow_html=True)

uploads = sb.file_uploader(
    "Upload documents",
    type=["txt", "md", "pdf", "docx", "csv", "json"],
    accept_multiple_files=True,
    key="kb_uploads",
    label_visibility="collapsed",
)

if uploads:
    if sb.button("📥 Ingest into knowledge base", key="ingest_btn", width="stretch"):
        progress = sb.progress(0.0, text="Uploading…")
        ok_count, fail_count = 0, 0
        for i, f in enumerate(uploads):
            success, info = upload_document(f, st.session_state.session_id)
            if success:
                ok_count += 1
                log_event("info", f"📥 Ingested {f.name}")
            else:
                fail_count += 1
                log_event("error", f"Ingest failed for {f.name}: {info}")
            progress.progress((i + 1) / len(uploads), text=f"Ingested {i + 1}/{len(uploads)}")
        progress.empty()
        if ok_count and not fail_count:
            st.toast(f"✅ Ingested {ok_count} file(s)", icon="📚")
        elif ok_count and fail_count:
            st.toast(f"⚠️ {ok_count} ok · {fail_count} failed", icon="📚")
        else:
            st.toast("❌ Ingest failed — check backend", icon="📚")
        st.session_state.uploaded_files.extend([f.name for f in uploads])

if st.session_state.uploaded_files:
    sb.caption(f"📎 {len(st.session_state.uploaded_files)} file(s) ingested this session")

# ---- Model & agent ----
sb.markdown('<div class="side-section">Model</div>', unsafe_allow_html=True)

MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "claude-3-5-sonnet", "llama-3.1-70b", "custom"]
st.session_state.model = sb.selectbox(
    "LLM",
    MODELS,
    index=MODELS.index(st.session_state.model) if st.session_state.model in MODELS else 0,
    label_visibility="collapsed",
)

st.session_state.agent_mode = sb.radio(
    "Agent mode",
    ["Fast", "Balanced", "Deep"],
    index=["Fast", "Balanced", "Deep"].index(st.session_state.agent_mode),
    horizontal=True,
    help="Fast: 1 pass. Balanced: retrieve + reason. Deep: multi-hop reasoning.",
)

# ---- Tools ----
sb.markdown('<div class="side-section">Tools</div>', unsafe_allow_html=True)
t1, t2, t3 = sb.columns(3)
with t1:
    st.session_state.tools_enabled["web_search"] = st.toggle(
        "🌐 Web", value=st.session_state.tools_enabled["web_search"],
    )
with t2:
    st.session_state.tools_enabled["calculator"] = st.toggle(
        "🧮 Calc", value=st.session_state.tools_enabled["calculator"],
    )
with t3:
    st.session_state.tools_enabled["code"] = st.toggle(
        "💻 Code", value=st.session_state.tools_enabled["code"],
    )

# ---- Persona ----
sb.markdown('<div class="side-section">Persona</div>', unsafe_allow_html=True)
st.session_state.system_prompt = sb.text_area(
    "System prompt",
    value=st.session_state.system_prompt,
    placeholder="You are a precise enterprise assistant…",
    height=80,
    label_visibility="collapsed",
)

# ---- Retrieval params ----
sb.markdown('<div class="side-section">Retrieval</div>', unsafe_allow_html=True)

st.session_state.top_k = sb.slider("📚 Top-K chunks", 1, 12, st.session_state.top_k, 1)
st.session_state.temperature = sb.slider("🌡 Temperature", 0.0, 1.0, st.session_state.temperature, 0.05)
st.session_state.request_timeout = sb.slider("⏱ Timeout (s)", 10, 180, st.session_state.request_timeout, 5)

# ---- UX prefs ----
sb.markdown('<div class="side-section">Preferences</div>', unsafe_allow_html=True)
st.session_state.stream_effect = sb.toggle("✨ Typewriter", value=st.session_state.stream_effect)
st.session_state.auto_scroll = sb.toggle("⬇️ Auto-scroll", value=st.session_state.auto_scroll)
st.session_state.compact_view = sb.toggle("📐 Compact view", value=st.session_state.compact_view)

# ---- Performance ----
sb.markdown('<div class="side-section">Performance</div>', unsafe_allow_html=True)
stats = latency_stats(st.session_state.latencies)
if stats:
    p1, p2 = sb.columns(2)
    with p1:
        sb.markdown(
            f'<div class="metric-card"><div class="v">{stats["avg"]:.2f}s</div>'
            f'<div class="k">Avg latency</div></div>',
            unsafe_allow_html=True,
        )
    with p2:
        sb.markdown(
            f'<div class="metric-card"><div class="v">{stats["last"]:.2f}s</div>'
            f'<div class="k">Last</div></div>',
            unsafe_allow_html=True,
        )
    sb.caption(f"min {stats['min']:.2f}s · max {stats['max']:.2f}s · n={stats['n']}")
else:
    sb.caption("No requests yet.")

tok = st.session_state.token_stats
if tok["total"] > 0:
    sb.caption(f"🎫 Tokens · prompt {tok['prompt']} · completion {tok['completion']} · total {tok['total']}")

# ---- Quick prompts ----
sb.markdown('<div class="side-section">Quick Prompts</div>', unsafe_allow_html=True)
QUICK = [
    ("📋", "Summarise the key policies"),
    ("🚀", "Onboarding steps for a new vendor"),
    ("⏰", "List compliance deadlines"),
    ("💸", "Explain the refund process"),
]
for icon, text in QUICK:
    if sb.button(f"{icon}  {text}", key=f"qp_{text}", width="stretch"):
        st.session_state._pending_prompt = text
        st.rerun()

# ---- Export ----
sb.markdown('<div class="side-section">Export</div>', unsafe_allow_html=True)
transcript = "\n\n".join(
    f"### {m['role'].title()}\n{m['content']}" for m in st.session_state.messages
)
sb.download_button(
    "⬇️ Markdown",
    data=transcript or "No messages yet.",
    file_name=f"chat_{st.session_state.session_id[:8]}.md",
    mime="text/markdown",
    width="stretch",
    disabled=not st.session_state.messages,
)
if st.session_state.messages:
    sb.download_button(
        "🧾 JSON",
        data=json.dumps(st.session_state.messages, indent=2, default=str),
        file_name=f"chat_{st.session_state.session_id[:8]}.json",
        mime="application/json",
        width="stretch",
    )

# ---- Danger zone ----
sb.markdown('<div class="side-section">Danger Zone</div>', unsafe_allow_html=True)
sb.markdown('<div class="danger-btn">', unsafe_allow_html=True)
if sb.button("🗑️ Clear History & Memory", width="stretch", key="clear_all"):
    log_event("warn", f"🗑️ Memory wipe: {st.session_state.session_id}")
    st.session_state.threads[st.session_state.session_id] = {
        "title": "New chat",
        "created": time.time(),
        "messages": [],
        "latencies": [],
    }
    st.session_state.messages = []
    st.session_state.latencies = []
    st.session_state.feedback = {}
    check_backend.clear()
    st.toast("History cleared", icon="🧹")
    st.rerun()
sb.markdown('</div>', unsafe_allow_html=True)

sb.markdown("<br>", unsafe_allow_html=True)
sb.caption("Built with ❤️ · Streamlit + Logfire")

# =====================================================================
#  MAIN AREA
# =====================================================================
if st.session_state.compact_view:
    st.markdown('<div class="compact">', unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
      <div class="badge-top">⚡ Multi-Agent · Retrieval · Reasoning</div>
      <h1><span class="accent">🧬</span> Advanced Agentic RAG</h1>
      <p>Retrieval-augmented reasoning over your documentation</p>
      <div class="rule"></div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

# ---- Search / filter ----
if st.session_state.messages:
    sc1, sc2 = st.columns([3, 1])
    with sc1:
        st.session_state.search_query = st.text_input(
            "Search history",
            value=st.session_state.search_query,
            placeholder="🔎 Filter messages…",
            label_visibility="collapsed",
        )
    with sc2:
        if st.button("↩️ Regenerate last answer", key="regen_main", width="stretch"):
            # remove last assistant message and re-run previous prompt
            msgs = st.session_state.messages
            if msgs and msgs[-1]["role"] == "assistant":
                msgs.pop()
            last_user = next((m for m in reversed(msgs) if m["role"] == "user"), None)
            if last_user:
                st.session_state._pending_prompt = last_user["content"]
                st.rerun()

# ---- Empty state + suggestions ----
SUGGESTIONS = [
    "Summarise the key policies in the knowledge base",
    "What are the onboarding steps for a new vendor?",
    "List any compliance deadlines mentioned",
    "Explain the refund process end-to-end",
]

if not st.session_state.messages:
    st.markdown(
        """
        <div class="empty-state">
          <div class="ico">🛰️</div>
          <h3>Your knowledge base is ready</h3>
          <p>Upload documents in the sidebar, then ask anything below.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    cols = st.columns(2)
    for i, s in enumerate(SUGGESTIONS):
        with cols[i % 2]:
            if st.button(s, key=f"sugg_{i}", width="stretch"):
                st.session_state._pending_prompt = s
                st.rerun()
    st.write("")

# ---- Chat history ----
q = (st.session_state.search_query or "").strip().lower()
for idx, message in enumerate(st.session_state.messages):
    if q and q not in message["content"].lower():
        continue

    avatar = AI_AVATAR if message["role"] == "assistant" else USER_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

        if message.get("steps"):
            with st.expander("🧠 Reasoning trace"):
                st.markdown(render_steps(message["steps"]), unsafe_allow_html=True)

        if message.get("sources"):
            render_sources(message["sources"])

        # per-message meta + actions
        if message["role"] == "assistant":
            meta_bits = []
            if message.get("meta"):    meta_bits.append(message["meta"])
            if message.get("tokens"):  meta_bits.append(f"🎫 {message['tokens']} tok")
            if message.get("model"):   meta_bits.append(f"🤖 {message['model']}")
            if meta_bits:
                st.caption(" · ".join(meta_bits))

            st.markdown('<div class="tiny-btn">', unsafe_allow_html=True)
            a1, a2, a3, a4 = st.columns([1, 1, 1, 6])
            with a1:
                if st.button("📋", key=f"copy_{idx}", help="Copy answer"):
                    st.toast("Copy the text above with Ctrl/Cmd+C", icon="📋")
            with a2:
                if st.button("👍", key=f"up_{idx}", help="Good answer"):
                    st.session_state.feedback[idx] = "up"
                    log_event("info", "👍 User feedback: positive", message_idx=idx)
                    st.toast("Thanks for the feedback!", icon="👍")
            with a3:
                if st.button("👎", key=f"down_{idx}", help="Bad answer"):
                    st.session_state.feedback[idx] = "down"
                    log_event("info", "👎 User feedback: negative", message_idx=idx)
                    st.toast("Thanks — we'll use this to improve.", icon="👎")
            with a4:
                fb = st.session_state.feedback.get(idx)
                if fb:
                    st.caption(f"Feedback: {'👍' if fb == 'up' else '👎'}")
            st.markdown('</div>', unsafe_allow_html=True)

# =====================================================================
#  CHAT INPUT
# =====================================================================
pending = st.session_state.pop("_pending_prompt", None)
prompt = st.chat_input("Ask about your documentation…")
if not prompt:
    prompt = pending

if prompt:
    with span("💬 User Chat Interaction", user_query=prompt,
              session_id=st.session_state.session_id):

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)

        data, err, elapsed, steps, sources = None, None, 0.0, [], []

        with st.chat_message("assistant", avatar=AI_AVATAR):
            with span("📡 Calling RAG Backend"):
                with st.status("🔍 Agent is thinking…", expanded=True) as status:
                    loader = st.empty()
                    loader.markdown(THINKING_HTML, unsafe_allow_html=True)

                    t0 = time.perf_counter()
                    try:
                        data = call_backend(
                            prompt,
                            st.session_state.session_id,
                            st.session_state.request_timeout,
                            st.session_state.top_k,
                            st.session_state.temperature,
                            model=st.session_state.model,
                            system_prompt=st.session_state.system_prompt or None,
                            tools=st.session_state.tools_enabled,
                            mode=st.session_state.agent_mode,
                        )
                    except Exception as e:
                        err = e
                    elapsed = time.perf_counter() - t0

                    loader.empty()

                    if err:
                        log_event("error", f"❌ UI-Backend Connection Failed: {err}")
                        status.update(label="❌ Connection failed", state="error", expanded=False)
                        st.error(
                            f"**Backend unreachable.**\n\n"
                            f"`{type(err).__name__}: {err}`\n\n"
                            f"Expected → `{BACKEND_URL}/query`"
                        )
                    else:
                        steps = data.get("thought_process") or []
                        if steps:
                            st.markdown(render_steps(steps), unsafe_allow_html=True)

                        status.update(
                            label=f"✅ Answer synthesized in {elapsed:.2f}s",
                            state="complete",
                            expanded=False,
                        )

                        sources = data.get("sources") or []
                        if sources:
                            render_sources(sources)

            if data is not None and not err:
                answer = data.get("answer") or "No response."
                placeholder = st.empty()
                if st.session_state.stream_effect:
                    typewriter(placeholder, answer)
                else:
                    placeholder.markdown(answer)

                # token usage
                usage = data.get("usage") or {}
                pt = usage.get("prompt_tokens", 0)
                ct = usage.get("completion_tokens", 0)
                tt = usage.get("total_tokens", pt + ct)
                if tt:
                    st.session_state.token_stats["prompt"]     += pt
                    st.session_state.token_stats["completion"] += ct
                    st.session_state.token_stats["total"]      += tt

                meta = f"⏱ {elapsed:.2f}s · 📚 {len(sources)} source(s) · 🌡 {st.session_state.temperature:.2f}"
                st.caption(meta)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "steps": steps,
                    "meta": meta,
                    "tokens": tt or None,
                    "model": st.session_state.model,
                })
                st.session_state.latencies.append(elapsed)

                # persist thread state
                persist_current()

                log_event("info", "✅ Chat cycle completed successfully.")

        if st.session_state.compact_view:
            st.markdown('</div>', unsafe_allow_html=True)
import streamlit as st
import google.generativeai as genai
import json, os, uuid, re, sqlite3, time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from google.api_core import exceptions as google_exceptions

# Load local .env
load_dotenv()
from core.graph_engine import app_graph
from core.llm_utils import run_llm_request

# ── MUST BE FIRST ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DialogueBot · ABHI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed", # Hide the standard sidebar
)

# ── DATABASE & PATHS ─────────────────────────────────────────────────────────────
DATA_DIR  = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "dialogue_store.db"
MASTER_PROMPT_PATH = Path("config") / "master_prompt.txt"
if not MASTER_PROMPT_PATH.parent.exists(): MASTER_PROMPT_PATH.parent.mkdir(parents=True)
if not MASTER_PROMPT_PATH.exists(): 
    MASTER_PROMPT_PATH.write_text("# Master Prompt\n- Be professional.", encoding="utf-8")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Clients table
    c.execute("""CREATE TABLE IF NOT EXISTS clients (
        id TEXT PRIMARY KEY,
        name TEXT,
        about TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    # Sessions table (now with client_id)
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        client_id TEXT,
        title TEXT,
        mode TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
    )""")
    # Messages table
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        content TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
    )""")
    # Migrate old DB if necessary
    try:
        c.execute("ALTER TABLE sessions ADD COLUMN client_id TEXT")
    except sqlite3.OperationalError:
        pass # already exists
    
    try:
        c.execute("""CREATE TABLE IF NOT EXISTS knowledge_base (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            type TEXT,
            name TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        )""")
    except Exception:
        pass

    # Pre-seed ABHI if empty
    c.execute("SELECT COUNT(*) FROM clients")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO clients (id, name, about) VALUES (?, ?, ?)", 
                  ("abhi-id", "Aditya Birla Health Insurance (ABHI)", "Aditya Birla Health Insurance Co. Limited (ABHI) is a provider of health insurance products in India."))
    
    conn.commit()
    conn.close()

init_db()

KB_FILE = DATA_DIR / "knowledge_base.json"
if not KB_FILE.exists():
    KB_FILE.write_text(json.dumps({"scripts": [], "dialogues": []}, ensure_ascii=False))

# ── CSS ──────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

:root {
    --bg-primary: #0a0a0b;
    --bg-secondary: #0f1115;
    --bg-tertiary: #161a23;
    --accent-blue: #4f8ef7;
    --accent-green: #34c77b;
    --text-main: #e2e4ed;
    --text-dim: #7a7d9a;
    --border-color: #1c1f2e;
    --glass-bg: rgba(15, 17, 23, 0.85);
    --glass-border: rgba(255, 255, 255, 0.08);
}

*, html, body { font-family: 'Inter', sans-serif; box-sizing: border-box; }
#MainMenu, footer, header { visibility: hidden; }
.stApp { background: var(--bg-primary); color: var(--text-main); }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-color);
    padding-top: 0 !important;
}
[data-testid="stSidebar"] > div { padding: 0 !important; }

.sb-logo {
    padding: 30px 24px 20px;
    border-bottom: 1px solid var(--border-color);
}
.sb-logo-text {
    font-family: 'Outfit', sans-serif;
    font-size: 1.4rem; font-weight: 700;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #4f8ef7, #34c77b);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.sb-logo-sub { font-size: 0.75rem; color: var(--text-dim); margin-top: 2px; font-weight: 500; }

.sb-new-chat { margin: 20px 20px 10px; }

.sb-section-label {
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: #454860;
    padding: 24px 24px 8px;
}

.hist-card {
    margin: 4px 14px;
    padding: 12px 16px;
    border-radius: 10px;
    border: 1px solid transparent;
    cursor: pointer;
    transition: all 0.2s ease;
    background: transparent;
}
.hist-card:hover { background: var(--bg-tertiary); border-color: var(--border-color); }
.hist-card.active { background: var(--bg-tertiary); border-color: var(--accent-blue); }
.hist-card-title { font-size: 0.85rem; font-weight: 500; color: #b0b3c8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hist-card-meta  { font-size: 0.72rem; color: #3a3d55; margin-top: 4px; }

/* ── Main layout ── */
.col-input  { padding-right: 16px; border-right: 1px solid var(--border-color); }
.col-output { padding-left: 16px; }

/* ── Section labels ── */
.field-label {
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--accent-blue);
    margin-bottom: 8px; margin-top: 24px;
}
.field-label:first-child { margin-top: 0; }

/* ── Inputs ── */
.stTextArea textarea, .stTextInput input {
    background: #13151f !important;
    border: 1px solid #1e2235 !important;
    border-radius: 12px !important;
    color: #e2e4ed !important;
    font-size: 0.9rem !important;
    line-height: 1.6 !important;
    padding: 12px 16px !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--accent-blue) !important;
    box-shadow: 0 0 0 2px rgba(79,142,247,0.15) !important;
}
.stTextArea label, .stTextInput label, .stSelectbox label {
    display: none !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: #13151f !important;
    border: 1px solid #1e2235 !important;
    border-radius: 12px !important;
    color: #e2e4ed !important;
    font-size: 0.88rem !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 12px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    transition: all 0.25s ease !important;
    border: none !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f8ef7 0%, #3b82f6 100%) !important;
    color: #fff !important;
    padding: 12px 0 !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(79,142,247,0.3) !important;
    opacity: 0.95 !important;
}
.stButton > button[kind="secondary"] {
    background: #13151f !important;
    border: 1px solid #1e2235 !important;
    color: #7a7d9a !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--accent-blue) !important;
    color: var(--accent-blue) !important;
}

/* ── Variation cards ── */
.var-wrap { margin-bottom: 14px; }
.var-card {
    border-radius: 16px;
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    backdrop-filter: blur(12px);
    overflow: hidden;
    transition: all 0.3s ease;
}
.var-card:hover { transform: translateY(-2px); border-color: var(--accent-blue); box-shadow: 0 12px 30px rgba(0,0,0,0.5); }

.var-head {
    padding: 14px 20px;
    display: flex; align-items: center; gap: 12px;
    border-bottom: 1px solid var(--glass-border);
}
.var-letter {
    width: 28px; height: 28px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700; flex-shrink: 0;
}
.var-title-text { font-family: 'Outfit', sans-serif; font-size: 0.92rem; font-weight: 600; }
.var-body { padding: 20px; font-size: 0.9rem; line-height: 1.75; white-space: pre-wrap; color: #b0b3c8; }

/* variation colour themes */
.v1 .var-letter { background: rgba(79,142,247,0.15); color: #4f8ef7; } .v1 .var-title-text { color: #4f8ef7; }
.v2 .var-letter { background: rgba(52,199,123,0.15); color: #34c77b; } .v2 .var-title-text { color: #34c77b; }
.v3 .var-letter { background: rgba(212,110,247,0.15); color: #d46ef7; } .v3 .var-title-text { color: #d46ef7; }
.v4 .var-letter { background: rgba(247,195,79,0.15); color: #f7c34f; } .v4 .var-title-text { color: #f7c34f; }
.v5 .var-letter { background: rgba(79,199,247,0.15); color: #4fc7f7; } .v5 .var-title-text { color: #4fc7f7; }

/* ── KB chips ── */
.kb-chip {
    font-size: 0.78rem; color: #7a7d9a;
    background: #13151f; border: 1px solid #1e2235;
    border-radius: 8px; padding: 6px 12px; margin: 4px 0;
    transition: all 0.2s;
}
.kb-chip:hover { border-color: var(--accent-blue); color: var(--text-main); }

hr { border-color: #1c1f2e !important; margin: 20px 0 !important; }

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0b0c10; }
::-webkit-scrollbar-thumb { background: #1e2235; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────────────
def ss(key, val):
    if key not in st.session_state:
        st.session_state[key] = val

ss("chat_id",    str(uuid.uuid4()))
ss("messages",   [])
ss("client_id",  "abhi-id")
ss("mode",       "dialogue")
ss("variations", None)
ss("about_val",  "")
ss("instr_val",  "")
ss("lang_val",   "Hinglish (Hindi + English)")
ss("history_index", 0)
ss("llm_provider", "Gemini") # Gemini | OpenAI | Claude | Groq | Cohere | Mistral | HuggingFace
ss("pending_new_chat", False)

# (LLM helpers now moved to core/llm_utils.py)

# ── DATA HELPERS ─────────────────────────────────────────────────────────────────
# ── DATABASE HELPERS ────────────────────────────────────────────────────────────
def db_get_clients():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, about FROM clients ORDER BY name ASC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "about": r[2]} for r in rows]

def db_add_client(name, about=""):
    cid = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO clients (id, name, about) VALUES (?, ?, ?)", (cid, name, about))
    conn.commit()
    conn.close()
    return cid

def db_update_client_about(cid, about):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE clients SET about = ? WHERE id = ?", (about, cid))
    conn.commit()
    conn.close()

def db_save_session(sid, cid, title, mode):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO sessions (id, client_id, title, mode) VALUES (?, ?, ?, ?)",
              (sid, cid, title, mode))
    conn.commit()
    conn.close()

def db_save_message(sid, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
              (sid, role, content))
    conn.commit()
    conn.close()

def db_get_sessions(cid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, mode, timestamp FROM sessions WHERE client_id = ? ORDER BY timestamp DESC LIMIT 15", (cid,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "mode": r[2], "timestamp": r[3]} for r in rows]

def db_get_messages(sid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (sid,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

def db_kb_save(cid, type, name, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO knowledge_base (id, client_id, type, name, content) VALUES (?, ?, ?, ?, ?)",
              (str(uuid.uuid4()), cid, type, name, content))
    conn.commit()
    conn.close()

def db_kb_get(cid, type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, content FROM knowledge_base WHERE client_id = ? AND type = ? ORDER BY timestamp DESC", (cid, type))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "content": r[2]} for r in rows]

def db_kb_delete(pk):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM knowledge_base WHERE id = ?", (pk,))
    conn.commit()
    conn.close()

def load_chat(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT title, mode, client_id FROM sessions WHERE id = ?", (chat_id,))
    row = c.fetchone()
    conn.close()
    if row:
        st.session_state.chat_id    = chat_id
        st.session_state.messages   = db_get_messages(chat_id)
        st.session_state.mode       = row[1]
        st.session_state.client_id  = row[2]
        st.session_state.variations = None
        for m in reversed(st.session_state.messages):
            if "## VARIATION" in m["content"]:
                st.session_state.variations = parse_variations(m["content"])
                break

def start_new_chat():
    st.session_state.chat_id    = str(uuid.uuid4())
    st.session_state.messages   = []
    st.session_state.variations = None
    st.session_state.about_val  = ""
    st.session_state.instr_val  = ""
    st.session_state.history_index = 0
    # Force clear widgets
    if "about_input" in st.session_state: st.session_state.about_input = ""
    if "instr_input" in st.session_state: st.session_state.instr_input = ""

# ── PARSING ───────────────────────────────────────────────────────────────────────
VARIATION_LABELS = ["a", "b", "c", "d", "e"]
VAR_CLASSES      = ["v1", "v2", "v3", "v4", "v5"]

def parse_variations(raw: str):
    parts = re.split(r'##\s*VARIATION\s*\d+[:\.\-]?\s*', raw, flags=re.IGNORECASE)
    out = []
    for part in parts[1:]:
        lines   = part.strip().split('\n')
        title   = lines[0].strip().lstrip('#').strip()
        content = '\n'.join(lines[1:]).strip()
        out.append({"title": title, "content": content})
    return out if out else [{"title": "Output", "content": raw.strip()}]

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────────
def build_system(mode: str, about: str) -> str:
    today = datetime.now().strftime("%B %d, %Y")
    cid = st.session_state.client_id
    
    # Load Master Prompt
    master = ""
    try:
        master = MASTER_PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        pass

    client_ctx = f"\n\nCLIENT CONTEXT:\n{about}" if about.strip() else ""

    kb_ref = ""
    if mode == "dialogue":
        items_db = db_kb_get(cid, "dialogue")
        if items_db:
            items = "\n\n---\n".join(f"[{d['name']}]\n{d['content']}" for d in items_db[:5])
            kb_ref = f"\n\nREFERENCE DIALOGUES FROM KNOWLEDGE BASE:\n{items}"
    else:  # script
        items_db = db_kb_get(cid, "script")
        if items_db:
            items = "\n\n---\n".join(f"[{s['name']}]\n{s['content']}" for s in items_db[:5])
            kb_ref = f"\n\nREFERENCE SCRIPTS FROM KNOWLEDGE BASE:\n{items}"

    base_instr = f"{master}\n\n" if master else ""
    
    if mode == "dialogue":
        return f"""{base_instr}You are a senior dialogue writer and sales communication expert. Today is {today}.
You write natural, spoken-language dialogues for voice bots and human agents.{client_ctx}{kb_ref}

OUTPUT RULES — follow these exactly:
1. Always produce EXACTLY 5 dialogue variations.
2. Label every variation with this exact heading format:   ## VARIATION N: TITLE
   Where N is 1–5 and TITLE is one of: SHORT & SWEET / PROFESSIONAL / FRIENDLY & CONVERSATIONAL / PERSUASIVE / EMPATHETIC
3. Each dialogue must have realistic back-and-forth lines, NOT just an agent monologue.
4. Use {{customer_name}}, {{agent_name}}, {{policy_expiry_date}} as placeholders.
5. Use the language/tone specified by the user."""

    else:  # script
        return f"""{base_instr}You are an expert conversation flow script architect for voice AI systems. Today is {today}.
You build structured [STEP_X] scripts with conditional branching (→), validation rules, and dialogue templates.{client_ctx}{kb_ref}

OUTPUT RULES — follow these exactly:
1. Always produce EXACTLY 5 script variations.
2. Label every variation with this exact heading format:   ## VARIATION N: TITLE
   Where N is 1–5 and TITLE is one of: MINIMAL / COMPREHENSIVE / CUSTOMER-CENTRIC / CONVERSION-OPTIMISED / OBJECTION-RECOVERY
3. Use [STEP_X] labels, → arrows for branching, {{{{placeholders}}}}.
4. Each script must be directly implementable in a voice AI pipeline."""

# ── AI GENERATE (AGENTIC VIA LANGGRAPH) ──────────────────────────────────────────
def run_generate(about, instructions, mode, language):
    # Prepare initial state for LangGraph
    master = ""
    try: master = MASTER_PROMPT_PATH.read_text(encoding="utf-8")
    except: pass
    
    # Pre-fetch KB for the Researcher Node
    kb_data = ""
    items_db = db_kb_get(st.session_state.client_id, "dialogue" if mode == "dialogue" else "script")
    if items_db:
        kb_data = "\n\n---\n".join(f"[{d['name']}]\n{d['content']}" for d in items_db[:5])

    initial_state = {
        "client_id": st.session_state.client_id,
        "about": about,
        "instructions": instructions,
        "mode": mode,
        "language": language,
        "provider": st.session_state.llm_provider,
        "master_prompt": master,
        "kb_context": kb_data,
        "draft": "",
        "audit_notes": "",
        "revision_count": 0,
        "final_output": ""
    }

    # Execute the Graph
    final_state = app_graph.invoke(initial_state)
    
    # If the graph output is empty, we fall back to a direct call as a safety measure
    if not final_state.get("final_output"):
        system = build_system(mode, about)
        prompt = f"LANGUAGE: {language}\n\n{instructions if instructions.strip() else 'Generate variations.'}"
        return run_llm_request(st.session_state.llm_provider, system, prompt)
    
    return final_state["final_output"]

def run_chat(user_msg, about, mode):
    system = build_system(mode, about)
    return run_llm_request(st.session_state.llm_provider, f"[System Instruction: {system[:500]}]", user_msg)

# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Logo
    st.markdown("""
    <div class="sb-logo">
        <div class="sb-logo-text">🎯 DialogueBot</div>
        <div class="sb-logo-sub">ABHI · Intelligence Hub</div>
    </div>
    """, unsafe_allow_html=True)

    # New Chat button
    st.markdown('<div class="sb-new-chat">', unsafe_allow_html=True)
    if st.button("＋  New Chat", use_container_width=True, type="primary", key="btn_new"):
        start_new_chat()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Chat History
    st.markdown('<div class="sb-section-label">Chat History</div>', unsafe_allow_html=True)
    history = db_get_sessions(st.session_state.client_id)
    if not history:
        st.markdown('<div style="padding:8px 18px;font-size:0.78rem;color:#3a3d55">No chats yet. Start typing!</div>', unsafe_allow_html=True)
    else:
        for ch in history:
            is_active = ch["id"] == st.session_state.chat_id
            cls = "hist-card active" if is_active else "hist-card"
            mode_icon = "💬" if ch.get("mode") == "dialogue" else "📋"
            ts = ch.get("timestamp", "")[:10]
            col_t, col_b = st.columns([5, 1])
            with col_t:
                st.markdown(f"""
                <div class="{cls}">
                    <div class="hist-card-title">{mode_icon} {ch.get('title','Untitled')[:42]}</div>
                    <div class="hist-card-meta">{ts}</div>
                </div>""", unsafe_allow_html=True)
            with col_b:
                if st.button("›", key=f"ch_{ch['id']}", help="Open"):
                    load_chat(ch["id"])
                    st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # Knowledge Base
    st.markdown('<div class="sb-section-label">Client Intelligence</div>', unsafe_allow_html=True)
    kb_tab1, kb_tab2 = st.tabs(["📋 Scripts", "💬 Dialogues"])

    with kb_tab1:
        scripts = db_kb_get(st.session_state.client_id, "script")
        st.caption(f"{len(scripts)} saved for this client")
        with st.expander("＋ Add Script"):
            sn = st.text_input("Name", key="sn", placeholder="e.g. Intro Pitch")
            sc = st.text_area("Content", key="sc", height=100)
            if st.button("Save", key="btn_ks"):
                if sc.strip():
                    db_kb_save(st.session_state.client_id, "script", sn or "New Script", sc.strip())
                    st.success("Saved!"); st.rerun()
        for i, s in enumerate(scripts[:8]):
            c1, c2 = st.columns([5, 1])
            with c1: st.markdown(f'<div class="kb-chip">📄 {s["name"][:30]}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("×", key=f"ks_{i}"):
                    db_kb_delete(s["id"]); st.rerun()

    with kb_tab2:
        dialogues = db_kb_get(st.session_state.client_id, "dialogue")
        st.caption(f"{len(dialogues)} saved for this client")
        with st.expander("＋ Add Dialogue"):
            dn = st.text_input("Name", key="dn", placeholder="e.g. Closing Script")
            dc = st.text_area("Content", key="dc", height=100)
            if st.button("Save", key="btn_kd"):
                if dc.strip():
                    db_kb_save(st.session_state.client_id, "dialogue", dn or "New Dialogue", dc.strip())
                    st.success("Saved!"); st.rerun()
        for i, d in enumerate(dialogues[:8]):
            c1, c2 = st.columns([5, 1])
            with c1: st.markdown(f'<div class="kb-chip">💬 {d["name"][:30]}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("×", key=f"kd_{i}"):
                    db_kb_delete(d["id"]); st.rerun()
    st.markdown("<hr>", unsafe_allow_html=True)

    # MASTER PROMPT EDITOR
    st.markdown('<div class="sb-section-label">⚙️ System Governance</div>', unsafe_allow_html=True)
    with st.expander("Master Instructions"):
        st.caption("Applied globally to all models")
        m_curr = MASTER_PROMPT_PATH.read_text(encoding="utf-8")
        m_new = st.text_area("Master Prompt", value=m_curr, height=250, key="master_p_input")
        if st.button("Save Master Rules"):
            MASTER_PROMPT_PATH.write_text(m_new, encoding="utf-8")
            st.success("Master Rules Updated!")
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN — two-column layout matching the sketch
# ─────────────────────────────────────────────────────────────────────────────
# ── MAIN — multi-client dashboard
hcol1, hcol_client, hcolM, hcol2 = st.columns([2.5, 2, 2, 1])
with hcol1:
    st.markdown('<h1 style="font-family:\'Outfit\',sans-serif;font-size:1.6rem;font-weight:700;margin:0;letter-spacing:-0.03em">DialogueBot<span style="color:var(--accent-blue)">.</span></h1>', unsafe_allow_html=True)

with hcol_client:
    # Client Selector List
    all_clients = db_get_clients()
    client_names = [c["name"] for c in all_clients] + ["＋ Add New Client"]
    current_idx = 0
    for i, c in enumerate(all_clients):
        if c["id"] == st.session_state.client_id:
            current_idx = i
            # Load client about into state if changed
            st.session_state.about_val = c["about"]
            break
            
    selected_client_name = st.selectbox(
        "Client", options=client_names, index=current_idx, label_visibility="collapsed"
    )
    
    if selected_client_name == "＋ Add New Client":
        with st.popover("Create New Client"):
            new_name = st.text_input("Brand Name", placeholder="e.g. LIC Insurance")
            new_about = st.text_area("Initial Context", placeholder="Describe the company...")
            if st.button("Create Client"):
                if new_name.strip():
                    new_id = db_add_client(new_name, new_about)
                    st.session_state.client_id = new_id
                    st.rerun()
    else:
        # Switch client if changed
        new_cid = next(c["id"] for c in all_clients if c["name"] == selected_client_name)
        if new_cid != st.session_state.client_id:
            st.session_state.client_id = new_cid
            st.rerun()

with hcolM:
    st.session_state.llm_provider = st.selectbox(
        "Model Selector",
        options=["Gemini", "OpenAI", "Claude", "Groq/Meta", "Cohere", "Mistral", "HuggingFace"],
        index=["Gemini", "OpenAI", "Claude", "Groq/Meta", "Cohere", "Mistral", "HuggingFace"].index(st.session_state.llm_provider),
        label_visibility="collapsed"
    )
with hcol2:
    if st.button("＋ New Chat", use_container_width=True, type="primary", key="main_new"):
        start_new_chat()
        st.rerun()

st.markdown("<hr style='margin:12px 0 24px'>", unsafe_allow_html=True)

# ── 3 COLUMN LAYOUT: HISTORY | INPUT | OUTCOME ──
col_hist, col_left, col_right = st.columns([1, 2, 2], gap="large")

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN 1 — Vertical History Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with col_hist:
    st.markdown('<div class="field-label" style="color:#7a7d9a">Session History</div>', unsafe_allow_html=True)
    sessions = db_get_sessions(st.session_state.client_id)
    if not sessions:
        st.markdown('<div style="font-size:0.75rem;color:#3a3d55;padding-top:10px">No history for this client.</div>', unsafe_allow_html=True)
    for s in sessions:
        is_active = s["id"] == st.session_state.chat_id
        icon = "💬" if s["mode"] == "dialogue" else "📋"
        btn_style = "secondary" if not is_active else "primary"
        if st.button(f"{icon} {s['title'][:25]}...", key=f"hist_{s['id']}", use_container_width=True, type=btn_style):
            load_chat(s["id"])
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN 2 — inputs
# ─────────────────────────────────────────────────────────────────────────────
with col_left:
    # ── ABOUT ──
    st.markdown('<div class="field-label">About — Define the Client</div>', unsafe_allow_html=True)
    about = st.text_area(
        "about", label_visibility="collapsed",
        value=st.session_state.about_val,
        height=120,
        placeholder=(
            "Describe the client / customer profile here…\n\n"
            "e.g. Male, 42 years, policy expired 3 months ago, last premium ₹18,000/yr, "
            "previously had individual plan with ABHI. May have switched to another provider."
        ),
        key="about_input",
    )

    # Save about to session so chat history title uses it
    if about != st.session_state.about_val:
        st.session_state.about_val = about

    # ── MODE — Script / Dialogue ──
    st.markdown('<div class="field-label">Type</div>', unsafe_allow_html=True)
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        if st.button(
            "💬 Dialogue",
            use_container_width=True,
            type="primary" if st.session_state.mode == "dialogue" else "secondary",
            key="btn_mode_d",
        ):
            if st.session_state.mode != "dialogue":
                st.session_state.mode = "dialogue"
                st.session_state.variations = None
                st.rerun()
    with m_col2:
        if st.button(
            "📋 Script",
            use_container_width=True,
            type="primary" if st.session_state.mode == "script" else "secondary",
            key="btn_mode_s",
        ):
            if st.session_state.mode != "script":
                st.session_state.mode = "script"
                st.session_state.variations = None
                st.rerun()

    # ── LANGUAGE ──
    st.markdown('<div class="field-label">Language</div>', unsafe_allow_html=True)
    language = st.selectbox(
        "lang", label_visibility="collapsed",
        options=["Hinglish (Hindi + English)", "Pure Hindi", "Pure English"],
        index=["Hinglish (Hindi + English)", "Pure Hindi", "Pure English"].index(st.session_state.lang_val),
        key="lang_select",
    )
    st.session_state.lang_val = language

    # ── INSTRUCTIONS ──
    st.markdown('<div class="field-label">Instructions — What do you want the bot to do?</div>', unsafe_allow_html=True)
    instructions = st.text_area(
        "instr", label_visibility="collapsed",
        value=st.session_state.instr_val,
        height=150,
        placeholder=(
            "Tell the bot what to generate…\n\n"
            "e.g. Generate a dialogue for when the customer says they already have LIC insurance "
            "and don't want to switch. Focus on porting benefits and the 10% discount offer."
        ),
        key="instr_input",
    )
    st.session_state.instr_val = instructions

    # ── GENERATE ──
    st.markdown("<br>", unsafe_allow_html=True)
    gen_label = f"✦ Generate {'Dialogues' if st.session_state.mode == 'dialogue' else 'Scripts'} (5 variations)"
    do_generate = st.button(gen_label, type="primary", use_container_width=True, key="btn_generate")

    # ── CHAT / REFINE SECTION ──
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="field-label">Chat & Refine</div>', unsafe_allow_html=True)

    # Show visible messages (skip meta tags)
    visible = [m for m in st.session_state.messages if not m["content"].startswith("[GENERATE")]
    
    if visible:
        # History Navigation (Show only if there's more than 1 turn to navigate)
        if len(visible) > 1:
            st.markdown('<div class="field-label">Conversation Navigator</div>', unsafe_allow_html=True)
            opts = list(range(len(visible)))
            st.session_state.history_index = st.select_slider(
                "Nav", 
                options=opts,
                value=st.session_state.history_index if st.session_state.history_index < len(visible) else len(visible)-1,
                label_visibility="collapsed",
                format_func=lambda x: f"Turn {x+1}",
                key=f"nav_select_{st.session_state.chat_id}_{len(visible)}"
            )
        else:
            st.session_state.history_index = 0

        # Display up to selected index
        for msg in visible[:st.session_state.history_index + 1]:
            if msg["role"] == "user":
                st.markdown(f"""
                <div style="background:var(--bg-tertiary);border:1px solid var(--border-color);border-radius:12px 12px 3px 12px;
                            padding:12px 16px;margin:8px 0 8px 32px;font-size:.9rem;color:var(--text-main);box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
                    <span style="font-size:1.1rem;margin-right:8px">🧑</span> {msg['content']}
                </div>""", unsafe_allow_html=True)
            else:
                content = msg["content"]
                # If it's the full variation block, show a summary in chat
                if "## VARIATION" in content:
                    st.markdown("""
                    <div style="background:#0f1117;border:1px dashed #2a2f50;border-radius:10px;
                                padding:8px 12px;margin:6px 24px 6px 0;font-size:.78rem;color:#4f8ef7;text-align:center;">
                        ✦ New variations generated (see right panel) ✦
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px 12px 12px 3px;
                                padding:12px 16px;margin:8px 32px 8px 0;font-size:.9rem;color:var(--text-dim);white-space:pre-wrap;box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
                        <span style="font-size:1.1rem;margin-right:8px">🤖</span> {content}
                    </div>""", unsafe_allow_html=True)

    follow_up = st.chat_input("Ask a follow-up or refine a variation…", key="chat_input")

# ─────────────────────────────────────────────────────────────────────────────
# HANDLE GENERATE (after UI rendered — no mid-render rerun)
# ─────────────────────────────────────────────────────────────────────────────
if do_generate:
    if not about.strip() and not instructions.strip():
        st.warning("Fill in at least the About or Instructions field first.")
    else:
        # Push about to chat history as first message if not already there
        first_msg = f"[CLIENT] {about.strip()[:120]}" if about.strip() else ""
        instr_msg = instructions.strip() or "Generate re-engagement call variations."
        combined  = f"{first_msg}\n\n[INSTRUCTIONS] {instr_msg}".strip()

        with st.spinner("Conducting research & architectural analysis..."):
            raw = run_generate(about, instructions, st.session_state.mode, language)
        if raw:
            st.session_state.messages.append({"role": "user",      "content": f"[GENERATE] {combined[:100]}"})
            st.session_state.messages.append({"role": "assistant", "content": raw})
            st.session_state.variations = parse_variations(raw)
            
            # Persist to DB
            first_user = next((m["content"] for m in st.session_state.messages if m["role"] == "user"), "New Chat")
            title = re.sub(r'\[.*?\]', '', first_user).strip()[:60] or "Untitled Chat"
            db_save_session(st.session_state.chat_id, st.session_state.client_id, title, st.session_state.mode)
            db_save_message(st.session_state.chat_id, "user", f"[GENERATE] {combined[:100]}")
            db_save_message(st.session_state.chat_id, "assistant", raw)
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# HANDLE CHAT FOLLOW-UP
# ─────────────────────────────────────────────────────────────────────────────
if follow_up:
    st.session_state.messages.append({"role": "user", "content": follow_up})
    with st.spinner("AI is thinking..."):
        bot_reply = run_chat(follow_up, about, st.session_state.mode)
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    db_save_message(st.session_state.chat_id, "user", follow_up)
    db_save_message(st.session_state.chat_id, "assistant", bot_reply)
    # Ensure session is saved if it's new
    db_save_session(st.session_state.chat_id, st.session_state.client_id, follow_up[:60] or "Chat", st.session_state.mode)
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN 3 — outcomes / variations
# ─────────────────────────────────────────────────────────────────────────────
with col_right:
    mode_badge = "dialogue" if st.session_state.mode == "dialogue" else "script"
    st.markdown(f"""
    <div class="field-label" style="display:flex; justify-content:space-between; align-items:center; margin-top:0">
        Generated Outcomes
        <span style="font-size:0.65rem; background:rgba(79,142,247,0.1); padding:2px 8px; border-radius:4px; border:1px solid rgba(79,142,247,0.2); color:var(--accent-blue)">{mode_badge.upper()} · 5 VARIATIONS</span>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.variations:
        st.markdown("""
        <div class="info-box">
            <div class="icon">✦</div>
            Fill in the <strong>About</strong> and <strong>Instructions</strong> on the left,
            choose your language, then hit <strong>Generate</strong>.<br><br>
            Your 5 variations will appear here as <strong>a · b · c · d · e</strong>.
        </div>""", unsafe_allow_html=True)
    else:
        for idx, var in enumerate(st.session_state.variations[:5]):
            letter = VARIATION_LABELS[idx] if idx < len(VARIATION_LABELS) else str(idx + 1)
            vcls   = VAR_CLASSES[idx]       if idx < len(VAR_CLASSES)      else "v1"
            title  = var.get("title", f"Variation {idx+1}")
            body   = var.get("content", "")

            st.markdown(f"""
            <div class="var-wrap">
                <div class="var-card {vcls}">
                    <div class="var-head">
                        <div class="var-letter">{letter})</div>
                        <div class="var-title-text">{title}</div>
                    </div>
                    <div class="var-body">{body}</div>
                </div>
            </div>""", unsafe_allow_html=True)

            # Action buttons per card
            b1, b2, b3 = st.columns([2, 2, 3])
            with b1:
                st.download_button(
                    "⬇ Download",
                    data=f"# {title}\n\n{body}",
                    file_name=f"var_{letter}_{st.session_state.mode}_{st.session_state.chat_id[:6]}.txt",
                    mime="text/plain",
                    key=f"dl_{idx}",
                    use_container_width=True,
                )
            with b2:
                if st.button("💾 Save to KB", key=f"kb_{idx}", use_container_width=True):
                    kb_fresh = load_kb()
                    entry = {"id": str(uuid.uuid4()), "name": title, "content": body, "added": datetime.now().isoformat()}
                    if st.session_state.mode == "dialogue":
                        kb_fresh["dialogues"].append(entry)
                    else:
                        kb_fresh["scripts"].append(entry)
                    if save_kb(kb_fresh):
                        st.toast(f"Saved '{title[:30]}' to KB!")

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:32px 0 16px;font-size:.7rem;color:#2a2d45;">
    DialogueBot · ABHI Voice Bot Optimizer · Gemini 1.5 Flash
</div>""", unsafe_allow_html=True)

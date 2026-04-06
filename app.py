import streamlit as st
import anthropic
import json
import os
import uuid
import re
from datetime import datetime
from pathlib import Path

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DialogueBot — ABHI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Paths ───────────────────────────────────────────────────────────────────────
DATA_DIR  = Path("data")
CHATS_DIR = DATA_DIR / "chats"
KB_FILE   = DATA_DIR / "knowledge_base.json"

for d in [DATA_DIR, CHATS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

if not KB_FILE.exists():
    KB_FILE.write_text(json.dumps({"scripts": [], "dialogues": []}, ensure_ascii=False))

# ─── Custom CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600&display=swap');

/* Base */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3, h4 { font-family: 'Syne', sans-serif; }

/* Hide default Streamlit header */
#MainMenu, footer { visibility: hidden; }
header { visibility: hidden; }

/* Main background */
.stApp { background: #0d0f14; color: #e8eaf0; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #111318 !important;
    border-right: 1px solid #1e2130;
}
[data-testid="stSidebar"] * { color: #c8cad8 !important; }

/* Header bar */
.app-header {
    background: linear-gradient(135deg, #1a1d2e 0%, #141720 100%);
    border: 1px solid #252840;
    border-radius: 16px;
    padding: 20px 28px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.app-header h1 {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    background: linear-gradient(135deg, #7c6fff, #ff6fb4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.app-header p { margin: 0; color: #7a7d8e; font-size: 0.85rem; }

/* Mode selector pills */
.mode-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 16px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.mode-badge.dialogue { background: #1a2040; color: #7c6fff; border: 1px solid #2d3560; }
.mode-badge.script   { background: #1a2a20; color: #4ecca3; border: 1px solid #2d5040; }

/* Cards */
.card {
    background: #111318;
    border: 1px solid #1e2130;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 16px;
    transition: border-color 0.2s;
}
.card:hover { border-color: #2d3560; }

/* Variation cards */
.var-card {
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
    border-left: 4px solid;
}
.var-1 { background: #12172b; border-color: #7c6fff; }
.var-2 { background: #12231a; border-color: #4ecca3; }
.var-3 { background: #231820; border-color: #ff6fb4; }
.var-4 { background: #1a1a12; border-color: #ffd166; }
.var-5 { background: #12202a; border-color: #06b6d4; }

.var-title {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.95rem;
    margin-bottom: 12px;
    letter-spacing: 0.03em;
}
.var-1 .var-title { color: #7c6fff; }
.var-2 .var-title { color: #4ecca3; }
.var-3 .var-title { color: #ff6fb4; }
.var-4 .var-title { color: #ffd166; }
.var-5 .var-title { color: #06b6d4; }

.var-content {
    color: #c8cad8;
    line-height: 1.7;
    white-space: pre-wrap;
    font-size: 0.9rem;
}

/* Chat messages */
.chat-msg-user {
    background: #1a1d2e;
    border: 1px solid #252840;
    border-radius: 12px 12px 4px 12px;
    padding: 12px 16px;
    margin: 8px 0 8px 40px;
    color: #e8eaf0;
    font-size: 0.9rem;
}
.chat-msg-bot {
    background: #111318;
    border: 1px solid #1e2130;
    border-radius: 12px 12px 12px 4px;
    padding: 12px 16px;
    margin: 8px 40px 8px 0;
    color: #c8cad8;
    font-size: 0.9rem;
}

/* KB items */
.kb-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #1a1d2e;
    border: 1px solid #252840;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 0.78rem;
    color: #9a9db0;
    margin: 3px 0;
    width: 100%;
}

/* History item */
.hist-item {
    background: #141720;
    border: 1px solid #1e2130;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 4px 0;
    cursor: pointer;
    transition: all 0.15s;
}
.hist-item:hover { background: #1a1d2e; border-color: #2d3560; }
.hist-title { font-size: 0.82rem; font-weight: 600; color: #c8cad8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hist-date  { font-size: 0.72rem; color: #5a5d70; margin-top: 2px; }

/* Info box */
.info-box {
    background: #12172b;
    border: 1px solid #252840;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 0.85rem;
    color: #9a9db0;
}

/* Buttons */
.stButton > button {
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c6fff, #a855f7) !important;
    border: none !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(124,111,255,0.35) !important;
}

/* Inputs */
.stTextArea textarea, .stTextInput input, .stSelectbox select {
    background: #111318 !important;
    border: 1px solid #1e2130 !important;
    border-radius: 10px !important;
    color: #e8eaf0 !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #7c6fff !important;
    box-shadow: 0 0 0 2px rgba(124,111,255,0.15) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #111318;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    color: #7a7d8e !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
}
.stTabs [aria-selected="true"] {
    background: #1a1d2e !important;
    color: #7c6fff !important;
}

/* Divider */
hr { border-color: #1e2130 !important; margin: 20px 0 !important; }

/* Spinner */
.stSpinner > div { border-top-color: #7c6fff !important; }

/* Labels */
.stTextArea label, .stTextInput label, .stSelectbox label {
    color: #7a7d8e !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
}

/* Section headers */
.section-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.78rem;
    font-weight: 700;
    color: #5a5d70;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid #1e2130;
}

/* Generate result section */
.gen-header {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #e8eaf0;
    margin: 24px 0 16px;
    display: flex;
    align-items: center;
    gap: 10px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d0f14; }
::-webkit-scrollbar-thumb { background: #252840; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3d4070; }
</style>
""", unsafe_allow_html=True)

# ─── Session State ────────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "current_chat_id": str(uuid.uuid4()),
        "messages": [],
        "generated_dialogues": None,
        "mode": "dialogue",
        "context_text": "",
        "instructions_text": "",
        "show_chat": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─── Helpers ──────────────────────────────────────────────────────────────────────
def get_client():
    try:
        key = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        st.error("⚠️ ANTHROPIC_API_KEY not found. Add it to Streamlit secrets or environment variables.")
        st.stop()
    return anthropic.Anthropic(api_key=key)

def load_kb():
    try:
        return json.loads(KB_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"scripts": [], "dialogues": []}

def save_kb(kb):
    KB_FILE.write_text(json.dumps(kb, indent=2, ensure_ascii=False))

def get_history():
    chats = []
    for f in sorted(CHATS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
        try:
            chats.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return chats

def save_chat():
    if not st.session_state.messages:
        return
    first_user = next((m["content"] for m in st.session_state.messages if m["role"] == "user"), "New Chat")
    # strip internal tags
    title = re.sub(r'\[.*?\]', '', first_user).strip()[:55]
    data = {
        "id": st.session_state.current_chat_id,
        "title": title or "Untitled Chat",
        "timestamp": datetime.now().isoformat(),
        "messages": st.session_state.messages,
        "mode": st.session_state.mode,
    }
    path = CHATS_DIR / f"{st.session_state.current_chat_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def load_chat(chat_id):
    f = CHATS_DIR / f"{chat_id}.json"
    if f.exists():
        data = json.loads(f.read_text(encoding="utf-8"))
        st.session_state.current_chat_id = chat_id
        st.session_state.messages = data.get("messages", [])
        st.session_state.mode = data.get("mode", "dialogue")
        st.session_state.generated_dialogues = None
        st.session_state.show_chat = True

def new_chat():
    save_chat()
    st.session_state.current_chat_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.generated_dialogues = None
    st.session_state.show_chat = False

# ─── System Prompt Builder ───────────────────────────────────────────────────────
def build_system(mode, kb):
    today = datetime.now().strftime("%B %d, %Y")

    if mode == "dialogue":
        kb_section = ""
        if kb.get("dialogues"):
            recent = kb["dialogues"][-6:]
            items = "\n\n---\n\n".join(
                f"[{d['name']}]\n{d['content']}" for d in recent
            )
            kb_section = f"\n\n═══ KNOWLEDGE BASE — REFERENCE DIALOGUES ═══\n{items}\n═══════════════════════════════════════════"

        return f"""You are an expert dialogue writer and senior sales communication specialist for Aditya Birla Health Insurance (ABHI). Today is {today}.

You write natural, human-sounding dialogues for voice chatbots and human agents — primarily in Hinglish (Hindi+English mix), unless instructed otherwise.

You think in natural language and respond conversationally. You understand insurance sales psychology, customer objection handling, and voice communication nuances.

WHEN GENERATING DIALOGUES — always produce EXACTLY 5 labeled variations:

## VARIATION 1: SHORT & SWEET
Brief, crisp, confident. Gets to the point in 2–4 exchanges. No fluff.

## VARIATION 2: PROFESSIONAL
Formal, structured, polished. Appropriate for business relationships. Uses respectful honorifics.

## VARIATION 3: FRIENDLY & CONVERSATIONAL
Warm, casual, relatable Hinglish. Feels like talking to a helpful friend, not a salesperson.

## VARIATION 4: PERSUASIVE
Benefit-led, creates urgency without pressure. Highlights key differentiators. Motivating language.

## VARIATION 5: EMPATHETIC
Deeply understanding of customer concerns. Validates feelings first, then guides gently toward solution.

Each dialogue must:
- Sound natural when spoken aloud (no awkward written phrases)
- Use {{customer_name}}, {{agent_name}}, {{policy_expiry_date}} placeholders where relevant
- Include realistic back-and-forth (not just agent monologues)
- Be immediately usable by a human agent or voice bot
- Match the language/tone style requested
{kb_section}"""

    else:  # script mode
        kb_section = ""
        if kb.get("scripts"):
            recent = kb["scripts"][-6:]
            items = "\n\n---\n\n".join(
                f"[{s['name']}]\n{s['content']}" for s in recent
            )
            kb_section = f"\n\n═══ KNOWLEDGE BASE — REFERENCE SCRIPTS ═══\n{items}\n══════════════════════════════════════════"

        return f"""You are an expert conversation script architect and prompt engineer for Aditya Birla Health Insurance (ABHI) voice AI systems. Today is {today}.

You design structured conversation flow scripts with step-based logic, conditional branching, validation rules, and dialogue templates — for implementation in production voice chatbot systems.

You think in natural language and communicate your reasoning clearly.

WHEN GENERATING SCRIPTS — always produce EXACTLY 5 labeled variations:

## VARIATION 1: MINIMAL SCRIPT
Streamlined flow with only essential steps. Fast, lean, low token cost. Ideal for simple re-engagement calls.

## VARIATION 2: COMPREHENSIVE SCRIPT
Full branching logic covering all edge cases: YES/NO/BUSY/VOICEMAIL/WRONG_PERSON/CALLBACK flows. Production-ready.

## VARIATION 3: CUSTOMER-CENTRIC SCRIPT
Prioritises customer journey and emotional experience. Extra empathy checkpoints. Graceful exit at every stage.

## VARIATION 4: CONVERSION-OPTIMISED SCRIPT
Every branch designed to maximise RM callback scheduling. Smart re-engagement on first rejection. Urgency woven in.

## VARIATION 5: OBJECTION-RECOVERY SCRIPT
Specialised for handling "not interested", "already have insurance", "too expensive" scenarios with layered persuasion logic.

Each script must:
- Follow the [STEP_X] format with clear dialogue and branching arrows (→)
- Include {{{{placeholder}}}} variables for dynamic data injection
- Specify validation rules (date/time ranges, etc.) where applicable
- Include NEXT_SAY tags for sequential dialogue chaining
- Be directly implementable in a voice AI pipeline
{kb_section}"""

# ─── Core AI Functions ────────────────────────────────────────────────────────────
VARIATION_COLORS = ["#7c6fff", "#4ecca3", "#ff6fb4", "#ffd166", "#06b6d4"]
VARIATION_CLASSES = ["var-1", "var-2", "var-3", "var-4", "var-5"]

def parse_variations(raw_text):
    parts = re.split(r'##\s+VARIATION\s+\d+[:\.]?\s*', raw_text)
    variations = []
    if len(parts) > 1:
        for part in parts[1:]:
            lines = part.strip().split('\n')
            title = lines[0].strip().lstrip('#').strip()
            content = '\n'.join(lines[1:]).strip()
            variations.append({"title": title, "content": content})
    return variations

def generate_variations(context, instructions, mode, kb, language, tone):
    client = get_client()
    system = build_system(mode, kb)

    full_prompt = f"""CONVERSATION CONTEXT / TRANSCRIPT:
{context if context.strip() else "(No specific transcript provided — generate based on instructions)"}

TASK INSTRUCTIONS:
{instructions if instructions.strip() else "Generate appropriate variations for an insurance customer re-engagement call."}

ADDITIONAL PREFERENCES:
- Language style: {language}
- Tone emphasis: {tone}

Now generate all 5 variations exactly as instructed in your system prompt. Label each clearly."""

    with st.spinner("✦ Generating variations…"):
        resp = get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": full_prompt}],
        )
    return resp.content[0].text

def chat_follow_up(user_msg, context, mode, kb):
    system = build_system(mode, kb)
    if context.strip():
        system += f"\n\n═══ SESSION CONTEXT ═══\n{context[:2000]}\n═══════════════════"

    st.session_state.messages.append({"role": "user", "content": user_msg})

    # Keep last 20 messages for context window
    history = st.session_state.messages[-20:]

    with st.spinner("✦ Thinking…"):
        resp = get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system,
            messages=history,
        )
    bot_msg = resp.content[0].text
    st.session_state.messages.append({"role": "assistant", "content": bot_msg})
    save_chat()
    return bot_msg

# ══════════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:12px 0 20px">
        <div style="font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:800;
                    background:linear-gradient(135deg,#7c6fff,#ff6fb4);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent">
            🎯 DialogueBot
        </div>
        <div style="font-size:0.75rem;color:#5a5d70;margin-top:2px">ABHI Voice Optimizer</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("＋  New Chat", use_container_width=True, type="primary"):
        new_chat()
        st.rerun()

    st.markdown('<div class="section-label" style="margin-top:20px">Recent Chats</div>', unsafe_allow_html=True)

    history = get_history()
    if not history:
        st.markdown('<div style="font-size:0.8rem;color:#5a5d70;padding:8px 0">No previous chats yet.</div>', unsafe_allow_html=True)
    for chat in history:
        is_active = chat["id"] == st.session_state.current_chat_id
        border = "border-color:#2d3560" if is_active else ""
        ts = chat.get("timestamp", "")[:10]
        mode_icon = "💬" if chat.get("mode") == "dialogue" else "📋"
        title = chat.get("title", "Untitled")[:40]
        col_a, col_b = st.columns([5, 1])
        with col_a:
            st.markdown(f"""
            <div class="hist-item" style="{border}">
                <div class="hist-title">{mode_icon} {title}</div>
                <div class="hist-date">{ts}</div>
            </div>""", unsafe_allow_html=True)
        with col_b:
            if st.button("›", key=f"open_{chat['id']}", help="Open this chat"):
                load_chat(chat["id"])
                st.rerun()

    st.markdown('<div class="section-label" style="margin-top:24px">Knowledge Base</div>', unsafe_allow_html=True)

    kb = load_kb()
    kb_tab1, kb_tab2 = st.tabs(["📋 Scripts", "💬 Dialogues"])

    with kb_tab1:
        st.markdown(f'<div style="font-size:0.75rem;color:#5a5d70;margin-bottom:8px">{len(kb["scripts"])} scripts stored</div>', unsafe_allow_html=True)
        with st.expander("＋ Add Script"):
            sn = st.text_input("Script name", key="sn", placeholder="e.g. Customer Regain v2")
            sc = st.text_area("Paste script content", key="sc", height=140)
            if st.button("Save Script", key="btn_ss"):
                if sc.strip():
                    kb["scripts"].append({
                        "id": str(uuid.uuid4()),
                        "name": sn or f"Script {len(kb['scripts'])+1}",
                        "content": sc.strip(),
                        "added": datetime.now().isoformat(),
                    })
                    save_kb(kb)
                    st.success("Saved!")
                    st.rerun()
        for i, s in enumerate(kb["scripts"][-8:]):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f'<div class="kb-chip">📄 {s["name"][:32]}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("×", key=f"ds_{i}", help="Delete"):
                    kb["scripts"] = [x for x in kb["scripts"] if x["id"] != s["id"]]
                    save_kb(kb)
                    st.rerun()

    with kb_tab2:
        st.markdown(f'<div style="font-size:0.75rem;color:#5a5d70;margin-bottom:8px">{len(kb["dialogues"])} dialogues stored</div>', unsafe_allow_html=True)
        with st.expander("＋ Add Dialogue"):
            dn = st.text_input("Dialogue name", key="dn", placeholder="e.g. Objection — Already Insured")
            dc = st.text_area("Paste dialogue content", key="dc", height=140)
            if st.button("Save Dialogue", key="btn_sd"):
                if dc.strip():
                    kb["dialogues"].append({
                        "id": str(uuid.uuid4()),
                        "name": dn or f"Dialogue {len(kb['dialogues'])+1}",
                        "content": dc.strip(),
                        "added": datetime.now().isoformat(),
                    })
                    save_kb(kb)
                    st.success("Saved!")
                    st.rerun()
        for i, d in enumerate(kb["dialogues"][-8:]):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f'<div class="kb-chip">💬 {d["name"][:32]}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("×", key=f"dd_{i}", help="Delete"):
                    kb["dialogues"] = [x for x in kb["dialogues"] if x["id"] != d["id"]]
                    save_kb(kb)
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════════
#  MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════════
kb = load_kb()
mode = st.session_state.mode

# Header
mode_color  = "#7c6fff" if mode == "dialogue" else "#4ecca3"
mode_label  = "DIALOGUE MODE" if mode == "dialogue" else "SCRIPT MODE"
mode_desc   = "Generating natural conversation dialogues for agents & voice bots" if mode == "dialogue" else "Generating structured conversation flow scripts with branching logic"

st.markdown(f"""
<div class="app-header">
    <div>
        <h1>DialogueBot</h1>
        <p>ABHI Voice Bot Prompt Optimizer — {mode_desc}</p>
    </div>
    <div style="margin-left:auto">
        <span class="mode-badge {'dialogue' if mode=='dialogue' else 'script'}"
              style="color:{mode_color}">● {mode_label}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Mode toggle
c1, c2, spacer = st.columns([2, 2, 6])
with c1:
    if st.button(
        "💬 Dialogue Mode",
        use_container_width=True,
        type="primary" if mode == "dialogue" else "secondary",
    ):
        st.session_state.mode = "dialogue"
        st.session_state.generated_dialogues = None
        st.rerun()
with c2:
    if st.button(
        "📋 Script Mode",
        use_container_width=True,
        type="primary" if mode == "script" else "secondary",
    ):
        st.session_state.mode = "script"
        st.session_state.generated_dialogues = None
        st.rerun()

st.markdown('<hr>', unsafe_allow_html=True)

# ─── Input Section ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">INPUT</div>', unsafe_allow_html=True)

col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    st.markdown("**Conversation Context / Transcript**")
    ctx_placeholder = (
        "Paste the customer–bot conversation transcript here…\n\n"
        "Example:\nAgent: Hello, am I speaking with Rahul ji?\n"
        "Customer: Haan, kaun bol raha hai?\n"
        "Agent: Main ABHI se call kar rahi hoon…\nCustomer: Mujhe interest nahi."
    )
    context = st.text_area(
        "context_area",
        value=st.session_state.context_text,
        height=220,
        placeholder=ctx_placeholder,
        label_visibility="collapsed",
        key="ctx_input",
    )
    st.session_state.context_text = context

with col_right:
    st.markdown("**Instructions for the Bot**")
    instr_placeholder = (
        "Tell the bot what to do…\n\n"
        "e.g. Generate a dialogue for when the customer says they already have insurance "
        "from LIC and don't want to switch. Focus on the porting benefits."
    )
    instructions = st.text_area(
        "instructions_area",
        value=st.session_state.instructions_text,
        height=120,
        placeholder=instr_placeholder,
        label_visibility="collapsed",
        key="instr_input",
    )
    st.session_state.instructions_text = instructions

    st.markdown("**Preferences**")
    pcol1, pcol2 = st.columns(2)
    with pcol1:
        language = st.selectbox(
            "Language Style",
            ["Hinglish (Hindi + English)", "Pure Hindi", "Pure English"],
            label_visibility="collapsed",
        )
    with pcol2:
        tone = st.selectbox(
            "Tone Emphasis",
            ["Balanced", "More Formal", "More Casual", "More Persuasive", "More Empathetic"],
            label_visibility="collapsed",
        )

st.markdown("<br>", unsafe_allow_html=True)
generate_clicked = st.button(
    f"✦ Generate 5 {'Dialogue' if mode == 'dialogue' else 'Script'} Variations",
    type="primary",
    use_container_width=True,
)

# ─── Generate ────────────────────────────────────────────────────────────────────
if generate_clicked:
    if not context.strip() and not instructions.strip():
        st.warning("Please provide at least a context or instructions to get started.")
    else:
        raw = generate_variations(context, instructions, mode, kb, language, tone)
        st.session_state.generated_dialogues = raw
        st.session_state.show_chat = True

        # Store in chat history
        summary = (instructions[:80] if instructions.strip() else context[:80]) + "…"
        st.session_state.messages.append({
            "role": "user",
            "content": f"[GENERATE {mode.upper()}] {summary}",
        })
        st.session_state.messages.append({
            "role": "assistant",
            "content": raw,
        })
        save_chat()

# ─── Display Variations ──────────────────────────────────────────────────────────
if st.session_state.generated_dialogues:
    raw = st.session_state.generated_dialogues
    variations = parse_variations(raw)

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown(f'<div class="gen-header">✦ Generated {"Dialogue" if mode=="dialogue" else "Script"} Variations</div>', unsafe_allow_html=True)

    if not variations:
        # Fallback: show raw
        st.text_area("Raw Output", raw, height=400)
    else:
        var_tabs = st.tabs([f"V{i+1} · {v['title'][:22]}" for i, v in enumerate(variations)])
        for i, (tab, var) in enumerate(zip(var_tabs, variations)):
            with tab:
                cls = VARIATION_CLASSES[i] if i < len(VARIATION_CLASSES) else "var-1"
                col = VARIATION_COLORS[i] if i < len(VARIATION_COLORS) else "#7c6fff"
                st.markdown(f"""
                <div class="var-card {cls}">
                    <div class="var-title">{var['title']}</div>
                    <div class="var-content">{var['content']}</div>
                </div>
                """, unsafe_allow_html=True)

                btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 4])
                with btn_col1:
                    st.download_button(
                        f"⬇ Download",
                        data=f"# {var['title']}\n\n{var['content']}",
                        file_name=f"v{i+1}_{mode}_{st.session_state.current_chat_id[:8]}.txt",
                        mime="text/plain",
                        key=f"dl_{i}",
                        use_container_width=True,
                    )
                with btn_col2:
                    if st.button("💾 Save to KB", key=f"kb_{i}", use_container_width=True):
                        kb_fresh = load_kb()
                        entry = {
                            "id": str(uuid.uuid4()),
                            "name": var["title"],
                            "content": var["content"],
                            "added": datetime.now().isoformat(),
                        }
                        if mode == "dialogue":
                            kb_fresh["dialogues"].append(entry)
                        else:
                            kb_fresh["scripts"].append(entry)
                        save_kb(kb_fresh)
                        st.success("Saved to Knowledge Base!")

# ─── Chat Section ────────────────────────────────────────────────────────────────
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown('<div class="section-label">CHAT & REFINE</div>', unsafe_allow_html=True)

visible_msgs = [
    m for m in st.session_state.messages
    if not m["content"].startswith("[GENERATE")
]

if visible_msgs:
    for msg in visible_msgs[-16:]:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-msg-user">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            # Truncate long assistant messages in chat view
            content = msg["content"]
            if len(content) > 800:
                content = content[:800] + "\n\n*[Full output shown above in variations panel]*"
            st.markdown(f'<div class="chat-msg-bot">🤖 {content}</div>', unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="info-box">💡 Generate variations above, then ask follow-up questions here — '
        '"make V2 shorter", "add a callback scheduling part", "translate V3 to pure Hindi", etc.</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)
user_chat = st.chat_input("Ask a follow-up, request refinements, or ask anything about the script…")

if user_chat:
    with st.chat_message("user"):
        st.write(user_chat)
    response = chat_follow_up(user_chat, context, mode, kb)
    with st.chat_message("assistant"):
        st.write(response)
    st.rerun()

# ─── Footer ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:40px 0 20px;font-size:0.75rem;color:#3a3d50">
    DialogueBot · ABHI Voice Bot Optimizer · Built with Streamlit + Claude
</div>
""", unsafe_allow_html=True)



import streamlit as st
import google.generativeai as genai
import json
import os
import uuid
import re
from datetime import datetime
from pathlib import Path

# ───────────────────────────────── Page Config ─────────────────────────────────
st.set_page_config(
    page_title="DialogueBot — ABHI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ───────────────────────────────── Paths ────────────────────────────────────────
DATA_DIR  = Path("data")
CHATS_DIR = DATA_DIR / "chats"
KB_FILE   = DATA_DIR / "knowledge_base.json"

for d in [DATA_DIR, CHATS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

if not KB_FILE.exists():
    KB_FILE.write_text(json.dumps({"scripts": [], "dialogues": []}, ensure_ascii=False))

# ───────────────────────────────── Gemini Init ──────────────────────────────────
def init_gemini():
    try:
        key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        key = os.environ.get("GEMINI_API_KEY", "")

    if not key:
        st.error("⚠️ GEMINI_API_KEY not found")
        st.stop()

    genai.configure(api_key=key)

init_gemini()

# ───────────────────────────────── Session State ────────────────────────────────
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

# ───────────────────────────────── Helpers ──────────────────────────────────────
def load_kb():
    try:
        return json.loads(KB_FILE.read_text(encoding="utf-8"))
    except:
        return {"scripts": [], "dialogues": []}

def save_kb(kb):
    KB_FILE.write_text(json.dumps(kb, indent=2, ensure_ascii=False))

def save_chat():
    if not st.session_state.messages:
        return
    first_user = next((m["content"] for m in st.session_state.messages if m["role"]=="user"), "New Chat")
    title = re.sub(r'\[.*?\]', '', first_user)[:55]
    data = {
        "id": st.session_state.current_chat_id,
        "title": title,
        "timestamp": datetime.now().isoformat(),
        "messages": st.session_state.messages,
        "mode": st.session_state.mode,
    }
    (CHATS_DIR / f"{st.session_state.current_chat_id}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False)
    )

def new_chat():
    save_chat()
    st.session_state.current_chat_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.generated_dialogues = None
    st.session_state.show_chat = False

# ───────────────────────────── System Prompt Builder ────────────────────────────
def build_system(mode, kb):
    today = datetime.now().strftime("%B %d, %Y")

    if mode == "dialogue":
        return f"""
You are an expert dialogue writer for Aditya Birla Health Insurance (ABHI).
Today is {today}.

Generate EXACTLY 5 variations:

VARIATION 1: SHORT & SWEET  
VARIATION 2: PROFESSIONAL  
VARIATION 3: FRIENDLY  
VARIATION 4: PERSUASIVE  
VARIATION 5: EMPATHETIC  

Use Hinglish by default.
Include placeholders {{customer_name}}, {{agent_name}}.
Sound natural when spoken.
"""
    else:
        return f"""
You are a voice-bot script architect for ABHI.
Today is {today}.

Generate EXACTLY 5 scripts with STEP based flows.
Include branching, placeholders, validation rules.
"""

# ───────────────────────────── Core AI Functions ────────────────────────────────
def generate_variations(context, instructions, mode, kb, language, tone):
    system = build_system(mode, kb)

    prompt = f"""
CONTEXT:
{context or "(none)"}

INSTRUCTIONS:
{instructions or "Generate insurance re-engagement content."}

Language: {language}
Tone: {tone}
"""

    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        system_instruction=system
    )

    with st.spinner("✦ Generating…"):
        res = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 4000,
                "top_p": 0.9
            }
        )

    return res.text

def chat_follow_up(user_msg, context, mode, kb):
    system = build_system(mode, kb)
    st.session_state.messages.append({"role": "user", "content": user_msg})

    history = ""
    for m in st.session_state.messages[-20:]:
        history += f"{m['role'].upper()}: {m['content']}\n"

    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        system_instruction=system
    )

    with st.spinner("✦ Thinking…"):
        res = model.generate_content(
            history,
            generation_config={
                "temperature": 0.6,
                "max_output_tokens": 2000
            }
        )

    bot = res.text
    st.session_state.messages.append({"role": "assistant", "content": bot})
    save_chat()
    return bot

# ───────────────────────────────── UI ───────────────────────────────────────────
st.title("🎯 DialogueBot — ABHI")

mode = st.radio("Mode", ["dialogue", "script"], horizontal=True)
st.session_state.mode = mode

context = st.text_area("Conversation Context", height=200)
instructions = st.text_area("Instructions", height=120)

language = st.selectbox("Language", ["Hinglish", "Hindi", "English"])
tone = st.selectbox("Tone", ["Balanced", "Formal", "Casual", "Persuasive", "Empathetic"])

if st.button("Generate 5 Variations", type="primary"):
    raw = generate_variations(context, instructions, mode, load_kb(), language, tone)
    st.session_state.generated_dialogues = raw
    st.session_state.messages += [
        {"role": "user", "content": instructions},
        {"role": "assistant", "content": raw}
    ]
    save_chat()

if st.session_state.generated_dialogues:
    st.markdown("### ✦ Output")
    st.text_area("Generated", st.session_state.generated_dialogues, height=500)

st.markdown("---")
st.markdown("### Chat & Refine")

user_msg = st.chat_input("Ask refinements…")
if user_msg:
    reply = chat_follow_up(user_msg, context, mode, load_kb())
    st.markdown(reply)
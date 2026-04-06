# 🎯 DialogueBot — ABHI Voice Bot Optimizer

A Streamlit app for ABHI prompt engineers and product managers to generate, refine, and manage dialogue & script variations for the voice chatbot system — powered by Claude (Anthropic).

---

## ✨ Features

- **Dialogue Mode** — Generates 5 natural conversation dialogue variations (Short & Sweet, Professional, Friendly, Persuasive, Empathetic)
- **Script Mode** — Generates 5 structured conversation flow scripts with branching logic
- **Knowledge Base** — Store and reuse reference scripts & dialogues; the AI learns from them
- **Chat & Refine** — Follow-up conversational chat to iterate on generated output
- **Chat History** — Last 10 sessions saved and reloadable
- **Download & Save** — Download any variation as `.txt` or save directly to the Knowledge Base
- **Dark UI** — Sleek, modern interface optimised for daily use

---

## 🚀 Deploy to Streamlit Cloud (Recommended)

### Step 1 — Push to GitHub

```bash
# From this folder
git init
git add .
git commit -m "Initial DialogueBot commit"

# Create a new repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/dialoguebot.git
git branch -M main
git push -u origin main
```

### Step 2 — Connect to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **New app**
3. Select your GitHub repo → branch `main` → main file `app.py`
4. Click **Advanced settings**

### Step 3 — Add Your API Key (Secret)

In **Advanced settings → Secrets**, paste:

```toml
ANTHROPIC_API_KEY = "sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx"
```

Click **Deploy!**

---

## 🛠 Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-xxxxxxxx"

# Or create .streamlit/secrets.toml (never commit this!)
# [default]
# ANTHROPIC_API_KEY = "sk-ant-xxxxxxxx"

# Run
streamlit run app.py
```

---

## 📁 Project Structure

```
dialoguebot/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── .streamlit/
│   ├── config.toml           # Theme & server config
│   └── secrets.toml          # ⚠️ LOCAL ONLY — never commit
├── data/
│   ├── knowledge_base.json   # Stored scripts & dialogues
│   └── chats/                # Saved chat sessions (up to 10)
├── .gitignore
└── README.md
```

---

## 🔄 Updating the App

Any changes pushed to your `main` branch on GitHub will automatically redeploy on Streamlit Cloud within ~1 minute.

```bash
git add .
git commit -m "Update: improved system prompt for script mode"
git push
```

---

## 📝 How to Use

### Generating Variations

1. Select **Dialogue Mode** (natural speech) or **Script Mode** (branching logic)
2. Paste a conversation transcript in the **Context** box
3. Type instructions in the **Instructions** box — e.g. *"Generate for when customer says they already have LIC policy"*
4. Set language & tone preferences
5. Click **Generate 5 Variations**

### Knowledge Base

- Add reference scripts/dialogues via the sidebar
- The AI will automatically use them as examples when generating new content
- Save any generated variation back to the KB with **Save to KB**

### Chat & Refine

After generating, use the chat box to:
- "Make V2 shorter and more direct"
- "Translate V3 to pure Hindi"
- "Add a callback scheduling section to V4"
- "What's the best approach if the customer is very reluctant?"

---

## ⚙️ Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required) |

---

## 📌 Notes

- **Knowledge Base** is stored in `data/knowledge_base.json` — on Streamlit Cloud, this resets on each deployment. For persistent KB, consider exporting to JSON and re-importing, or upgrading to a database (Supabase, Firebase, etc.)
- **Chat History** similarly resets on redeployment — sessions are meant to be used within a working session
- Model used: `claude-sonnet-4-20250514`

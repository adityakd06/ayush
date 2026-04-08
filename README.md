# 🎯 DialogueBot · Enterprise Edition

DialogueBot is a high-performance **Multi-Tenant Agentic Platform** designed to optimize voice AI dialogues and scripts at scale. It transforms raw business context into high-conversion AI dialogues through an autonomous orchestration layer.

---

## 🏗️ The Architecture: "How it's Made"

DialogueBot is built on a **3-Layer Architecture** that ensures data isolation, consistent governance, and self-correcting intelligence.

1.  **Orchestration (LangGraph):** The "Brain." It uses advanced state-graphs to move from simple generation to an agentic loop (**Plan → Research → Draft → Audit → Revise**).
2.  **Infrastructure (SQLite & Streamlit):** A robust multi-tenant database partitioned by `client_id`, ensuring every brand's history and knowledge base remains strictly isolated.
3.  **Intelligence Hub (Unified LLM):** A centralized hub connecting **7 elite LLM providers** (Gemini 2.5/3.1, Claude 3.5, OpenAI, Groq, Cohere, Mistral, and Hugging Face) with automatic failover and quota-hunting logic.

---

## 🔁 "In & Out": The Data Flow

### 📥 Inputs (What goes In):
-   **Client Context ("About"):** The core identity and unique selling proposition of the brand.
-   **Knowledge Base (KB):** Reference scripts, past dialogues, and specialized edge cases stored in the multi-tenant DB.
-   **Governance ("Master Prompt"):** Global instructions that enforce brand tone, formatting rules, and "Universal Laws" across all models.
-   **Task Instructions:** Specific user requests for the AI to execute.

### 📤 Outputs (What comes Out):
-   **5 Optimized Variations:** High-quality, diverse dialogue options labeled with `## VARIATION N`.
-   **VoIP-Ready Formatting:** Scripts are automatically enriched with `{{placeholders}}` for direct implementation in voice AI pipelines.
-   **Self-Audited Content:** Every output has been vetted by an internal "Auditor AI" to ensure it matches the Master Prompt before being displayed.

---

## 🛠️ Built With:
-   **Framework:** [Streamlit](https://streamlit.io/) (Premium Dark Mode UI)
-   **Agentic Logic:** [LangGraph](https://github.com/langchain-ai/langgraph) (Self-Correction Loops)
-   **Database:** [SQLite](https://www.sqlite.org/) (Multi-Tenant Persistent Storage)
-   **Intelligence:** Integrated API Hub (Gemini 2.5/3.1, GPT-4o, Claude 3.5 Sonnet, Llama 3.3, Mistral Large)

---

## ⚖️ Why This Exists?
In enterprise Voice AI, consistency is the hardest challenge. Variations in model behavior can break pipelines. DialogueBot solves this by:
1.  **Centralizing Governance:** One Master Prompt to rule all models.
2.  **Ensuring Quality:** Automated self-auditing ensures no script is missing a placeholder.
3.  **Scaling Clients:** Manage 100+ clients from a single interface with perfect data isolation.

---

### 🚀 Getting Started
1. Install dependencies: `pip install -r requirements.txt`
2. Configure keys in `.env` or Streamlit Secrets.
3. Run: `streamlit run app.py`

*Powered by the LangGraph Autonomous Engine.*

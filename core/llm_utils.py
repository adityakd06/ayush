import os
import streamlit as st

def run_llm_request(provider: str, system_prompt: str, user_prompt: str) -> str:
    """Centralized LLM request handler for all 7 providers."""
    
    # ── GOOGLE GEMINI ──
    if provider == "Gemini":
        try:
            import google.generativeai as genai
        except ImportError: return "Model Error: 'google-generativeai' not installed."
        key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key: return "Error: Missing Google/Gemini API Key."
        genai.configure(api_key=key)
        # Auto-discover the best model available for this key (Prioritizing 2.5 and 3.1)
        try:
            available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # Preference order (Updated with your advanced tier models)
            pref = [
                "models/gemini-3.1-pro-preview", 
                "models/gemini-2.5-pro", 
                "models/gemini-2.5-flash", 
                "models/gemini-2.0-flash",
                "models/gemini-1.5-pro",
                "models/gemini-1.5-flash"
            ]
            
            best = "gemini-pro" # fallback
            for p in pref:
                if p in available:
                    best = p
                    break
            model = genai.GenerativeModel(best, system_instruction=system_prompt)
        except:
            model = genai.GenerativeModel('gemini-pro', system_instruction=system_prompt)
        
        try:
            resp = model.generate_content(user_prompt)
            return resp.text
        except Exception as e:
            return f"Gemini Error: {e}"

    # ── OPENAI ──
    elif provider == "OpenAI":
        try:
            import openai
        except ImportError: return "Model Error: 'openai' not installed."
        key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not key: return "Error: Missing OpenAI API Key."
        client = openai.OpenAI(api_key=key)
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role":"system","content":system_prompt}, {"role":"user","content":user_prompt}]
            )
            return resp.choices[0].message.content
        except Exception as e: return f"OpenAI Error: {e}"

    # ── ANTHROPIC CLAUDE ──
    elif provider == "Claude":
        try:
            import anthropic
        except ImportError: return "Model Error: 'anthropic' not installed."
        key = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not key: return "Error: Missing Anthropic API Key."
        client = anthropic.Anthropic(api_key=key)
        try:
            resp = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role":"user","content":user_prompt}]
            )
            return resp.content[0].text
        except Exception as e: return f"Claude Error: {e}"

    # ── GROQ (META LLAMA) ──
    elif provider == "Groq/Meta":
        try:
            import groq
        except ImportError: return "Model Error: 'groq' not installed."
        key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
        if not key: return "Error: Missing Groq API Key."
        client = groq.Groq(api_key=key)
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"system","content":system_prompt}, {"role":"user","content":user_prompt}]
            )
            return resp.choices[0].message.content
        except Exception as e: return f"Groq Error: {e}"

    # ── COHERE ──
    elif provider == "Cohere":
        try: import cohere
        except ImportError: return "Model Error: 'cohere' not installed."
        key = st.secrets.get("COHERE_API_KEY") or os.environ.get("COHERE_API_KEY")
        if not key: return "Error: Missing Cohere API Key."
        client = cohere.Client(api_key=key)
        try:
            resp = client.chat(message=f"{system_prompt}\n\n{user_prompt}", model="command-r-plus-08-2024")
            return resp.text
        except Exception as e: return f"Cohere Error: {e}"

    # ── MISTRAL ──
    elif provider == "Mistral":
        try:
            from mistralai.client import MistralClient
            from mistralai.models.chat_completion import ChatMessage
        except ImportError: return "Model Error: 'mistralai' not installed."
        key = st.secrets.get("MISTRAL_API_KEY") or os.environ.get("MISTRAL_API_KEY")
        if not key: return "Error: Missing Mistral API Key."
        client = MistralClient(api_key=key)
        try:
            resp = client.chat(
                model="mistral-large-latest",
                messages=[ChatMessage(role="system", content=system_prompt), ChatMessage(role="user", content=user_prompt)]
            )
            return resp.choices[0].message.content
        except Exception as e: return f"Mistral Error: {e}"

    # ── HUGGING FACE ──
    elif provider == "HuggingFace":
        try:
            from huggingface_hub import InferenceClient
        except ImportError: return "Model Error: 'huggingface_hub' not installed."
        key = st.secrets.get("HF_API_KEY") or st.secrets.get("HUGGINGFACE_API_KEY") or os.environ.get("HF_API_KEY")
        if not key: return "Error: Missing Hugging Face API Key."
        client = InferenceClient(api_key=key)
        try:
            resp = client.chat_completion(
                model="Qwen/Qwen2.5-72B-Instruct",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=4096
            )
            return resp.choices[0].message.content
        except Exception as e: return f"Hugging Face Error: {e}"

    return "Error: Unknown Provider"

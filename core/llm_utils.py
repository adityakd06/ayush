import os
import streamlit as st
import time

def run_llm_request(provider: str, system_prompt: str, user_prompt: str) -> str:
    """Centralized LLM request handler for all 7 providers."""
    
    # ── GOOGLE GEMINI (With Auto-Failover Logic) ──
    if provider == "Gemini":
        try:
            import google.generativeai as genai
            from google.api_core import exceptions as google_exceptions
        except ImportError: return "Model Error: 'google-generativeai' not installed."
        
        key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key: return "Error: Missing Google/Gemini API Key."
        
        genai.configure(api_key=key)
        
        # 1. Get all models that support generation
        try:
            all_available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except Exception as e:
            return f"Gemini Error (Listing Models): {e}"

        # 2. Define priority hierarchy (Prioritizing Flash for best quota availability)
        priority_map = [
            "models/gemini-2.5-flash", 
            "models/gemini-2.0-flash",
            "models/gemini-1.5-flash",
            "models/gemini-flash-latest",
            "models/gemini-2.5-pro", 
            "models/gemini-1.5-pro",
            "models/gemini-pro"
        ]
        
        # Filter available models by our priority list
        to_try = [p for p in priority_map if p in all_available]
        # Add any other available models that weren't in our map, just in case
        for m in all_available:
            if m not in to_try: to_try.append(m)

        # 3. Sequential Execution Loop (The "One-Shot Fix")
        last_error = "No supported models found."
        for model_name in to_try:
            try:
                model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
                resp = model.generate_content(user_prompt)
                if resp and resp.text:
                    return resp.text
            except (google_exceptions.ResourceExhausted, google_exceptions.InvalidArgument, google_exceptions.NotFound) as e:
                # Capture 429s (Quota), 400s (Unsupported), 404s (Not Found)
                last_error = f"Model {model_name} failed (Quota/Found). Trying next... ({e})"
                continue # Try next model
            except Exception as e:
                # Critical logic error or API issue
                return f"Gemini Critical Error ({model_name}): {e}"
        
        return f"Gemini Error: Exhausted all available models. Last error: {last_error}"

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

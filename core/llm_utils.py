import os
import streamlit as st

def run_llm_request(provider: str, system_prompt: str, user_prompt: str) -> str:
    """Centralized LLM request handler for all providers."""
    
    if provider == "Gemini":
        try:
            import google.generativeai as genai
        except ImportError:
            return "Model Error: 'google-generativeai' not installed."
        key = st.secrets.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key: return "Error: Missing Google API Key."
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_prompt)
        try:
            resp = model.generate_content(user_prompt)
            return resp.text
        except Exception as e:
            return f"Gemini Error: {e}"

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

    return "Error: Unknown Provider"

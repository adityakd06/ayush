import os
from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, END
from datetime import datetime

# Define the State
class GraphState(TypedDict):
    client_id: str
    about: str
    instructions: str
    mode: str
    language: str
    provider: str
    master_prompt: str
    kb_context: str
    draft: str
    audit_notes: str
    revision_count: int
    final_output: str

from core.llm_utils import run_llm_request

# ── NODES ──────────────────────────────────────────────────────────────────

def generator_node(state: GraphState):
    """Generates the initial 5 variations."""
    print("--- GENERATING VARIATIONS ---")
    
    # Construct the instruction set
    system = f"{state['master_prompt']}\n\nYou are a {state['mode']} architect.\n\n"
    system += f"CONTEXT:\n{state['about']}\n\nKNOWLEDGE BASE:\n{state['kb_context']}\n\n"
    
    user_prompt = f"LANGUAGE: {state['language']}\n\n{state['instructions']}"
    if state['audit_notes'] and state['audit_notes'] != "Passed":
        user_prompt += f"\n\nCRITICAL FIX REQUIRED FROM AUDIT:\n{state['audit_notes']}\nPlease regenerate with these fixes."

    output = run_llm_request(state['provider'], system, user_prompt)
    
    return {"draft": output, "final_output": output}

def auditor_node(state: GraphState):
    """Checks if the draft meets the Master Prompt requirements."""
    print("--- AUDITING OUTPUT ---")
    draft = state.get("draft", "")
    revision_count = state.get("revision_count", 0)
    
    # Audit logic: Check for structural elements
    has_headers = "## VARIATION" in draft
    has_placeholders = "{{" in draft
    
    if (has_headers and has_placeholders) or revision_count >= 1:
        return {"audit_notes": "Passed"}
    else:
        notes = "The output failed our quality check."
        if not has_headers: notes += " Missing '## VARIATION N' headers."
        if not has_placeholders: notes += " Missing double-bracket placeholders {{}}."
        return {"audit_notes": notes, "revision_count": revision_count + 1}

def should_revise(state: GraphState):
    """Routing logic."""
    if state["audit_notes"] == "Passed":
        return "end"
    else:
        return "revise"

# ── COMPILE GRAPH ──────────────────────────────────────────────────────────

def build_workflow():
    workflow = StateGraph(GraphState)
    
    workflow.add_node("generator", generator_node)
    workflow.add_node("auditor", auditor_node)
    
    workflow.set_entry_point("generator")
    workflow.add_edge("generator", "auditor")
    
    workflow.add_conditional_edges(
        "auditor",
        should_revise,
        {
            "revise": "generator",
            "end": END
        }
    )
    
    return workflow.compile()

app_graph = build_workflow()

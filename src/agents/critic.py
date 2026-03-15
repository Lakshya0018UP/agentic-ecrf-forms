import json
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from src.utils.state import AgentState
from dotenv import load_dotenv

load_dotenv()

def critic_node(state: AgentState) -> AgentState:
    """The Critic Agent: Reviews the form for errors using Gemini."""
    if not state.draft_form:
        state.is_valid = False
        return state

    print(f"--- AUDITING FORM {state.draft_form.form_name} ---")

    import time
    time.sleep(2) # Pacing for Rate Limits
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, max_retries=5)
    form_json = state.draft_form.model_dump_json() if hasattr(state.draft_form, 'model_dump_json') else state.draft_form.json()
    
    prompt = f"""
    Clinical Data Auditor Task: Review {state.current_domain} form JSON.
    
    FORM:
    {form_json}
    
    CRITERIA:
    1. Mandatory fields (STUDYID, VISIT, {state.current_domain}DAT, {state.current_domain}PERF) present?
    2. Aligns with: {state.protocol_summary}
    3. CLINICAL COMPLETENESS: Does the form have enough fields (at least 5-10) to collect the necessary data for {state.current_domain}? (e.g., for VS, it should have BP, Pulse, Temp, etc. For AE, it should have Term, Severity, Outcome, etc.)
    
    RESPONSE: 'PASS' if ALL criteria met, otherwise a clear list of missing fields/fixes.
    """
    
    try:
        response = llm.invoke(prompt)
        result = response.content.strip()
        
        if "PASS" in result:
            state.is_valid = True
            state.final_forms.append(state.draft_form)
        else:
            state.is_valid = False
            state.errors.append(result)
    except Exception as e:
        state.errors.append(f"Critic Error: {str(e)}")
        
    return state

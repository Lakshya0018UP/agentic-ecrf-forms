import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from src.utils.state import AgentState
from src.utils.json_utils import extract_json
from dotenv import load_dotenv

load_dotenv()

def protocol_analyzer_node(state: AgentState) -> AgentState:
    """Consolidated node to extract Study Metadata, Visit Schedule, and Assessment Mapping in ONE call."""
    print("--- ANALYZING PROTOCOL STRUCTURE (Consolidated) ---")
    
    import time
    time.sleep(2) # Increased Pacing for Rate Limits
    
    # Switched to 2.5-flash as requested by user
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, max_output_tokens=2048, max_retries=5)
    
    prompt = f"""
    SYSTEM: You are an expert Clinical Data Manager. Your task is to extract BOTH the global study structure and the requirements for the {state.current_domain} domain.
    
    CONTEXT:
    {state.extracted_context[:12000]}
    
    TASK:
    Extract and return ONLY a valid JSON object. 
    - "study_info" and "visit_schedule" are GLOBAL to the protocol.
    - CRITICAL: The "indication" is the primary condition or disease being studied (e.g., "Type 2 Diabetes", "Healthy Volunteers"). 
      Look for "Condition", "Indication", or "Target Population". DO NOT return "N/A" if any disease/condition is mentioned in the context.
    - "protocol_summary" and "assessment_map" should focus on {state.current_domain}.
    
    Structure for "visit_schedule" (CRITICAL):
    "visit_schedule": [
        {{
          "visit_id": "V1",
          "visit_name": "Screening",
          "visit_number": 1,
          "target_day": 1,
          "window": "+/- 3 days"
        }}
    ]
    
    Structure for "assessment_map":
    "assessment_map": {{
        "{state.current_domain}": ["Screening", "Day 1", "Week 2"]
      }}
    
    IMPORTANT: If you find a Schedule of Activities (SoA) table, extract ALL visits.
    Return ONLY JSON. NO COMMENTS.
    """
    
    try:
        response = llm.invoke(prompt)
        data = extract_json(response.content)
        
        if not data:
            raise ValueError(f"No valid JSON found in analyzer response. Start: {response.content[:50]}")

        # ROBUST KEY MAPPING: Handle variations in LLM output
        # 1. Normalize root keys
        if "data" in data and isinstance(data["data"], dict):
            data = data["data"]
            
        # 2. Check for alternative visit schedule keys
        potential_visit_keys = ["visit_schedule", "schedule_of_activities", "soa", "visits", "visit_plan", "study_visits"]
        found_visits = []
        for key in potential_visit_keys:
            if key in data and isinstance(data[key], list) and len(data[key]) > 0:
                raw_visits = data[key]
                # Ensure each visit is a dictionary
                for v in raw_visits:
                    if isinstance(v, dict):
                        # Map internal keys to expected ones if they differ
                        if 'visit' in v and 'visit_name' not in v: v['visit_name'] = v['visit']
                        if 'day' in v and 'target_day' not in v: v['target_day'] = v['day']
                        if 'id' in v and 'visit_id' not in v: v['visit_id'] = v['id']
                        found_visits.append(v)
                    elif isinstance(v, str):
                        found_visits.append({"visit_name": v, "visit_id": v, "target_day": "N/A", "window": "N/A"})
                break
        
        # Merge or Update Study Info
        new_study_info = data.get('study_info', {})
        if new_study_info:
            for k, v in new_study_info.items():
                if v and v != "N/A":
                    state.study_info[k] = v
        
        # Map YAML study_title to internal title if needed
        if "study_title" in state.study_info and "title" not in state.study_info:
            state.study_info["title"] = state.study_info["study_title"]
            
        # Update Visit Schedule only if we found something new or it was empty
        if found_visits:
            # Helper to count valid/populated visits
            def count_valid(v_list):
                count = 0
                for v in v_list:
                    if isinstance(v, dict) and (v.get('visit_name') or v.get('visit_id')):
                        count += 1
                return count

            # If we already have a schedule, only replace it if the new one is more complete
            if not state.visit_schedule or count_valid(found_visits) >= count_valid(state.visit_schedule):
                state.visit_schedule = found_visits
            
        # Update Assessment Map
        new_assessment_map = data.get('assessment_map', {})
        if new_assessment_map:
            state.assessment_map.update(new_assessment_map)
            
        # Handle protocol_summary robustly (it must be a string in AgentState)
        new_summary = data.get('protocol_summary')
        if isinstance(new_summary, dict):
            # If it's a dict, try to get the current domain's summary or just join all values
            state.protocol_summary = new_summary.get(state.current_domain, str(new_summary))
        elif new_summary:
            state.protocol_summary = str(new_summary)
            
        state.extraction_notes.extend(data.get('extraction_notes', []))
        
        # PRUNING: Clear the raw context to save thousands of tokens in next steps
        state.extracted_context = "" 
        
    except Exception as e:
        state.errors.append(f"Analyzer Error: {str(e)}")
        
    return state


def researcher_node(state: AgentState) -> AgentState:
    """Queries Qdrant for both Global Protocol Structure and Domain-Specific details."""
    print(f"--- RESEARCHING PROTOCOL & DOMAIN: {state.current_domain} ---")
    
    embedding = OllamaEmbeddings(model="nomic-embed-text")
    qdrant = QdrantVectorStore.from_existing_collection(
        embedding=embedding,
        collection_name="protocol_collection",
        url="http://localhost:6333"
    )
    
    # 1. Search for Global Study Structure (Focus on Indication and Metadata)
    global_query = "Protocol Title, Study Indication, Disease, Objectives, and Complete Metadata"
    global_results = qdrant.similarity_search(global_query, k=8)
    
    # 2. Search for Domain-to-Visit Mapping (Specifically which visits {state.current_domain} occurs at)
    mapping_query = f"At which visits is {state.current_domain} (or its assessments) required? List the specific visit names."
    mapping_results = qdrant.similarity_search(mapping_query, k=4)
    
    # 3. Search for Domain-Specific Procedures
    domain_query = f"{state.current_domain} assessment procedures and collection requirements"
    domain_results = qdrant.similarity_search(domain_query, k=4)
    
    # Combine results
    combined_results = global_results + mapping_results + domain_results
    state.extracted_context = "\n\n".join([r.page_content for r in combined_results])
    
    return state

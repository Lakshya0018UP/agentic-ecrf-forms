import json
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from src.utils.state import AgentState, eCRFForm
from src.tools.cdash_tool import CDASHTool
from src.utils.json_utils import extract_json
from dotenv import load_dotenv

load_dotenv()

def designer_node(state: AgentState) -> AgentState:
    """The Designer Agent: Generates JSON using Gemini."""
    print(f"--- DESIGNING FORM FOR {state.current_domain} (Iteration {state.iterations}) ---")

    import time
    time.sleep(2) # Pacing for Rate Limits

    # 1. Inject CDASH Standards
    cdash = CDASHTool(standards_dir="data/standards")
    fields = cdash.get_domain_fields(state.current_domain)
    
    # Get codelists for categorical fields
    field_ids = [f['name'] for f in fields[:25]]
    codelists = cdash.get_codelists(field_ids)
    
    # Organize codelists by field_name for prompt
    cl_map = {}
    for cl in codelists:
        fn = cl['field_name']
        if fn not in cl_map: cl_map[fn] = []
        cl_map[fn].append({'code': cl['code'], 'label': cl['display']})
    
    # STANDARDS (Use these IDs and Codelists):
    # We provide up to 25 fields to ensure a comprehensive form can be built
    prompt_standards = []
    for f in fields[:25]:
        prompt_standards.append({
            'id': f['name'], 
            'label': f['label'], 
            'codelist': cl_map.get(f['name'])
        })

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, max_output_tokens=4096, max_retries=5)

    prompt = f"""
    SYSTEM: You are an expert Clinical Data Manager.
    
    TASK: Review the provided CDASH standards for the {state.current_domain} domain and the clinical protocol.
    Your goal is to define which fields are REQUIRED and to add any PROTOCOL-SPECIFIC fields.
    
    CRITICAL RULES:
    1. Mandatory Header Fields: STUDYID, VISIT, {state.current_domain}PERF, {state.current_domain}DAT.
    2. You MUST use the provided Standard IDs.
    3. Return a JSON object containing the 'fields' you've reviewed or added.
    
    CONTEXT:
    - Protocol: {state.study_info.get('protocol_number')}
    - Visits: {[v.get('visit_name') for v in state.visit_schedule[:10]]}
    
    AVAILABLE STANDARDS:
    {json.dumps(prompt_standards)}
    
    Return ONLY a JSON object with a "fields" list. Include ALL relevant standards.
    """
    
    state.iterations += 1
    
    try:
        response = llm.invoke(prompt)
        parsed_data = extract_json(response.content)
        
        if not parsed_data:
            raise ValueError(f"No valid JSON found in response.")

        # Helper to normalize field IDs (e.g., VS_HORIZONTAL_VSPERF -> VSPERF)
        def normalize_id(fid, domain):
            fid = fid.upper()
            # If the ID contains the domain and a suffix like PERF or DAT, prefer the suffix
            # Pattern: DOMAIN_..._SUFFIX
            if domain.upper() in fid:
                parts = fid.split('_')
                # If the last part is a known standard suffix, use it
                if parts[-1] in ["PERF", "DAT", "STAT", "TERM", "ORRES", "ORRESU", "LOC", "POS"]:
                    return parts[-1] if parts[-1] in ["STUDYID", "VISIT"] else domain.upper() + parts[-1]
                # If the ID starts with Domain_ and has multiple parts, try to take the most specific part
                if len(parts) > 1 and parts[0] == domain.upper():
                    # Check if the last part is the core variable name
                    # e.g. VS_HORIZONTAL_SYSBP_VSORRES -> VSORRES is not right, SYSBP is better
                    # But CDASH says VSORRES is the result.
                    pass
            return fid

        # 1. Start with ALL Standard Fields as a base to ensure completeness
        final_fields_map = {}
        for s in prompt_standards:
            # Clean ID logic
            full_id = s['id'].upper()
            clean_id = full_id
            if "_" in full_id:
                # If it contains the domain and ends with a standard suffix
                # e.g. VS_HORIZONTAL_VSPERF -> VSPERF
                for suffix in ["PERF", "DAT", "STAT", "TERM", "LOC", "POS"]:
                    if full_id.endswith(suffix) and state.current_domain.upper() in full_id:
                        clean_id = state.current_domain.upper() + suffix
                        break
            
            final_fields_map[clean_id] = {
                "field_id": clean_id,
                "label": s['label'],
                "data_type": "Char",
                "control_type": "text",
                "required": False,
                "codelist": s['codelist'],
                "protocol_specific": False
            }

        # 2. Overlay LLM suggestions
        llm_fields = []
        if isinstance(parsed_data, list): llm_fields = parsed_data
        elif isinstance(parsed_data, dict):
            if "fields" in parsed_data: llm_fields = parsed_data["fields"]
            else: llm_fields = [v for k, v in parsed_data.items() if isinstance(v, dict)]

        for lf in llm_fields:
            raw_fid = lf.get("field_id", lf.get("id", lf.get("variable", ""))).upper()
            if not raw_fid: continue
            
            fid = raw_fid
            # Basic mapping for LLM variations
            if fid == "DATE": fid = f"{state.current_domain}DAT"
            if fid == "PERFORMED": fid = f"{state.current_domain}PERF"
            
            # If it's a standard field (or normalized version), update it
            if fid in final_fields_map:
                for attr in ["label", "data_type", "control_type", "required", "codelist"]:
                    if attr in lf: final_fields_map[fid][attr] = lf[attr]
            else:
                # If it's a new protocol-specific field, add it
                final_fields_map[fid] = {
                    "field_id": fid,
                    "label": lf.get("label", fid),
                    "data_type": lf.get("data_type", "Char"),
                    "control_type": lf.get("control_type", "text"),
                    "required": lf.get("required", False),
                    "codelist": lf.get("codelist"),
                    "protocol_specific": True
                }

        # 3. Add Mandatory Headers (Safety Layer)
        mandatory = [
            ("STUDYID", "Study Identifier", "Char", "text"),
            ("VISIT", "Visit Name", "Char", "text"),
            (f"{state.current_domain}PERF", f"Was {state.current_domain} performed?", "Char", "radio"),
            (f"{state.current_domain}DAT", "Assessment Date", "Date", "datePicker")
        ]
        for fid, lbl, dtype, ctrl in mandatory:
            if fid not in final_fields_map:
                final_fields_map[fid] = {
                    "field_id": fid, "label": lbl, "data_type": dtype, "control_type": ctrl, "required": True, "protocol_specific": False
                }
            else:
                final_fields_map[fid]["required"] = True # Force mandatory
                if dtype == "Date": final_fields_map[fid]["data_type"] = dtype
                if ctrl == "datePicker": final_fields_map[fid]["control_type"] = ctrl

        # 4. Final list construction (Header fields first)
        header_ids = ["STUDYID", "VISIT", f"{state.current_domain}PERF", f"{state.current_domain}DAT"]
        ordered_fields = []
        
        # Add headers in order
        for hid in header_ids:
            if hid in final_fields_map:
                ordered_fields.append(final_fields_map.pop(hid))
        
        # Add remaining standard and custom fields
        ordered_fields.extend(final_fields_map.values())

        # 5. Extract Applicable Visits for this domain
        applicable_visits = []
        # Look for domain name or assessment name matches in assessment_map
        # e.g. "Vital Signs" or "VS"
        for key, visits in state.assessment_map.items():
            if state.current_domain.lower() in key.lower() or key.lower() in state.current_domain.lower():
                if isinstance(visits, list):
                    applicable_visits = visits
                    break
        
        # Fallback: if map is empty, list all visit names from schedule
        if not applicable_visits and state.visit_schedule:
            applicable_visits = [v.get('visit_name', v.get('visit_id', 'Unknown')) for v in state.visit_schedule]

        normalized_data = {
            "form_id": state.current_domain + "_FORM",
            "form_name": state.current_domain + " Assessment",
            "domain": state.current_domain,
            "fields": ordered_fields,
            "applicable_visits": applicable_visits
        }

        print(f"DEBUG: Designer finalized {len(normalized_data['fields'])} fields and {len(applicable_visits)} visits for {state.current_domain}")
        state.draft_form = eCRFForm(**normalized_data)
    except Exception as e:
        state.errors.append(f"Designer Error: {str(e)}")
        state.draft_form = None 
        
    return state


import os
import json
from src.utils.state import AgentState
from src.utils.report_generator import generate_docx_report

def reporter_node(state: AgentState) -> AgentState:
    """The Reporter Agent: Saves both .docx and .json versions of the eCRF."""
    print("--- GENERATING FINAL OUTPUTS ---")
    
    # Ensure outputs folder exists
    os.makedirs("outputs/json", exist_ok=True)
    os.makedirs("outputs/reports", exist_ok=True)
    
    if not state.final_forms and state.draft_form:
        state.final_forms = [state.draft_form]
    
    if not state.final_forms:
        state.errors.append("Reporter Error: No forms available to generate output.")
        return state
        
    # 1. Save .docx Report
    docx_filename = f"outputs/reports/eCRF_Specification_{state.current_domain}.docx"
    try:
        generate_docx_report(
            state.final_forms, 
            filename=docx_filename,
            study_info=state.study_info,
            # visit_schedule=state.visit_schedule,
            # assessment_map=state.assessment_map
        )
        print(f"Report saved to: {docx_filename}")
    except Exception as e:
        state.errors.append(f"Reporter Docx Error: {str(e)}")

    # 2. Save .json Definition
    json_filename = f"outputs/json/eCRF_Definition_{state.current_domain}.json"
    try:
        # Convert models to dict for JSON serialization
        forms_data = [f.model_dump() if hasattr(f, 'model_dump') else f.dict() for f in state.final_forms]
        
        # Include metadata in JSON
        json_output = {
            "study_info": state.study_info,
            # "visit_schedule": state.visit_schedule,
            # "assessment_map": state.assessment_map,
            "forms": forms_data
        }
        
        with open(json_filename, "w") as jf:
            json.dump(json_output, jf, indent=4)
        print(f"JSON definition saved to: {json_filename}")
    except Exception as e:
        state.errors.append(f"Reporter JSON Error: {str(e)}")
        
    return state

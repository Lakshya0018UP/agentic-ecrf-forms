
import os
import json
from src.agents.designer import designer_node
from src.utils.state import AgentState
from dotenv import load_dotenv

load_dotenv()

def test_designer_logic():
    print("--- TESTING DESIGNER GENERATION ---")
    
    # Create a mock state with the data the designer needs
    state = AgentState(
        current_domain="VS",
        study_info={"protocol_number": "TEST-123"},
        visit_schedule=[{"visit_name": "Screening"}, {"visit_name": "Baseline"}],
        protocol_summary="Collect systolic and diastolic blood pressure, heart rate, and temperature at all visits."
    )
    
    # Run the designer node
    updated_state = designer_node(state)
    
    if updated_state.draft_form:
        print("SUCCESS: Form generated!")
        print(f"Form Name: {updated_state.draft_form.form_name}")
        print(f"Fields found: {[f.field_id for f in updated_state.draft_form.fields]}")
    else:
        print("FAILED: No form generated.")
        if updated_state.errors:
            print(f"Errors: {updated_state.errors[-1]}")

if __name__ == "__main__":
    test_designer_logic()

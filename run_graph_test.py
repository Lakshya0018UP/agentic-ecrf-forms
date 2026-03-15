import os
import json
from src.graph import create_graph
from src.utils.state import AgentState

def test_full_workflow():
    print("--- STARTING FULL WORKFLOW TEST ---")
    
    # Initialize the graph
    app = create_graph()
    
    # Create initial state for a common domain (e.g., Vital Signs)
    initial_state = AgentState(
        current_domain="VS",
        protocol_path="data/protocol/Protocol _ARN-509-003_PRO_Redacted.pdf"
    )
    
    print(f"Invoking graph for domain: {initial_state.current_domain}")
    
    try:
        # Run the graph
        # We use a config to limit recursion depth if needed, but the graph handles iterations
        final_state = app.invoke(initial_state)
        
        print("\n--- WORKFLOW COMPLETE ---")
        print(f"Is Valid: {final_state.get('is_valid')}")
        print(f"Iterations: {final_state.get('iterations')}")
        
        if final_state.get('final_forms'):
            form = final_state['final_forms'][-1]
            print(f"Generated Form: {form.form_name}")
            print(f"Number of fields: {len(form.fields)}")
        
        # Check if report was generated (Reporter agent should have saved it)
        report_file = f"outputs/reports/eCRF_Specification_{initial_state.current_domain}.docx"
        if os.path.exists(report_file):
            print(f"SUCCESS: Report found at {report_file}")
        else:
            print(f"WARNING: Report NOT found at {report_file}")
            
        if final_state.get('errors'):
            print("\nAudit Remarks/Errors:")
            for err in final_state['errors']:
                print(f"- {err}")
                
    except Exception as e:
        print(f"\nFATAL ERROR during graph invocation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_workflow()

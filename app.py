import streamlit as st
import os
import subprocess
from src.graph import create_graph
from src.utils.state import AgentState, eCRFForm
from src.utils.report_generator import generate_docx_report
from src.utils.clinical_trials_api import fetch_clinical_trial_data
from src.utils.form_renderer import render_form_html
from ingest import index_text_content

from qdrant_client import QdrantClient

st.set_page_config(page_title="AI eCRF Designer Pro", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for a professional look
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #004a99; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; background-color: #28a745; color: white; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ AI-Agentic eCRF Specification Designer")
st.markdown("---")

# Ensure output directory exists
os.makedirs("outputs/reports", exist_ok=True)
os.makedirs("data/protocol", exist_ok=True)

# Initialize session state for final_state and tracking
if 'final_state' not in st.session_state:
    st.session_state.final_state = None
if 'review_feedback' not in st.session_state:
    st.session_state.review_feedback = ""
if 'study_info' not in st.session_state:
    st.session_state.study_info = {}

# Qdrant Client for verification
client = QdrantClient(url="http://localhost:6333")

def check_indexing():
    try:
        collections = client.get_collections().collections
        return any(c.name == "protocol_collection" for c in collections)
    except:
        return False

# Sidebar Command Center
with st.sidebar:
    st.header("📋 Project Controls")
    
    # API Configuration
    st.subheader("🔑 API Setup")
    api_key = st.text_input("Enter Google API Key", type="password")
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
    
    st.markdown("---")
    
    # 1. Input Method
    st.subheader("1. Protocol Input")
    input_method = st.radio("Choose Method", ["API (ClinicalTrials.gov)", "Upload File (PDF/DOCX)"])
    
    if input_method == "API (ClinicalTrials.gov)":
        nct_id = st.text_input("Enter NCT ID (e.g. NCT04000165)")
        if st.button("🔍 Fetch & Index Protocol"):
            if not nct_id:
                st.error("Please enter an NCT ID")
            else:
                with st.spinner("Fetching data from ClinicalTrials.gov..."):
                    result = fetch_clinical_trial_data(nct_id)
                    if "error" in result:
                        st.error(f"API Error: {result['error']}")
                    else:
                        st.success(f"Fetched: {result['title']}")
                        st.session_state.study_info = {
                            "protocol_number": result.get("protocol_number"),
                            "indication": result.get("indication"),
                            "title": result.get("title"),
                            "phase": result.get("phase"),
                            "nct_id": result.get("nct_id")
                        }
                        index_text_content(result['full_text'], nct_id)
                        st.success("Indexing Complete!")
    
    else:
        uploaded_file = st.file_uploader("Upload Protocol", type=["pdf", "docx"])
        if uploaded_file:
            save_path = os.path.join("data/protocol", uploaded_file.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            if st.button("📚 Index Uploaded Protocol"):
                with st.spinner("Indexing..."):
                    result = subprocess.run([".\\venv\\Scripts\\python.exe", "ingest.py"], capture_output=True, text=True)
                    if result.returncode == 0:
                        st.success("Protocol Indexed Successfully!")
                    else:
                        st.error(f"Ingestion Failed: {result.stderr}")

    st.markdown("---")
    st.subheader("2. Generation Settings")
    domain = st.selectbox("🎯 Target Domain", ["VS", "AE", "DM", "LB", "MH", "CM", "EX"])
    
    if st.button("🚀 Run Multi-Agent Loop"):
        if not check_indexing():
            st.error("🚨 Indexing not detected!")
        else:
            app = create_graph()
            initial_state = AgentState(
                current_domain=domain,
                study_info=st.session_state.get('study_info', {})
            )
            
            with st.status(f"🛠️ Designing {domain} Form...", expanded=True) as status:
                for event in app.stream(initial_state):
                    for node_name, state_update in event.items():
                        st.write(f"✅ Node: **{node_name.title()}** completed.")
                        st.session_state.final_state = state_update
                status.update(label="✅ Loop Complete!", state="complete")
            st.rerun()

# Main Interface with Tabs
tab1, tab2 = st.tabs(["📊 Specification Dashboard", "🔍 Review & Refine"])

with tab1:
    if st.session_state.final_state:
        final_state = st.session_state.final_state
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(f"Generated {final_state.get('current_domain')} Form")
            if final_state.get('final_forms'):
                form_data = final_state['final_forms'][-1]
                # Ensure it's an eCRFForm object for the renderer
                if isinstance(form_data, dict):
                    form_obj = eCRFForm(**form_data)
                else:
                    form_obj = form_data
                
                # Show both HTML Form and Raw JSON Specification using expanders for clarity
                st.markdown("### Visual Form Preview")
                html_content = render_form_html(form_obj)
                st.markdown(html_content, unsafe_allow_html=True)
                
                with st.expander("📄 Raw JSON Specification"):
                    st.json(form_obj.model_dump() if hasattr(form_obj, 'model_dump') else form_obj)
                
            elif final_state.get('errors'):
                # Display the most recent error as the reason for failure
                st.error(f"⚠️ **Generation Failed:** {final_state['errors'][-1]}")
                st.info("Check the 'Review & Refine' tab for the full audit trail.")
            else:
                st.info("No forms generated yet.")
        
        with col2:
            st.subheader("Study Context")
            st.write(f"**Protocol:** {final_state.get('study_info', {}).get('protocol_number', 'N/A')}")
            st.write(f"**Indication:** {final_state.get('study_info', {}).get('indication', 'N/A')}")
            
            if st.button("📄 Export Final .docx Report"):
                forms = [eCRFForm(**f) if isinstance(f, dict) else f for f in final_state.get('final_forms', [])]
                out_filename = f"outputs/reports/eCRF_Specification_{final_state.get('current_domain')}.docx"
                report_path = generate_docx_report(
                    forms, 
                    filename=out_filename,
                    study_info=final_state.get('study_info'),
                    visit_schedule=final_state.get('visit_schedule'),
                    assessment_map=final_state.get('assessment_map')
                )
                with open(report_path, "rb") as file:
                    st.download_button(label="⬇️ Download Document", data=file, file_name=os.path.basename(report_path))

with tab2:
    st.subheader("Audit & Quality Review")
    if st.session_state.final_state:
        final_state = st.session_state.final_state
        
        # Display Audit Remarks
        st.markdown("### Agent Audit Trail")
        for err in final_state.get('errors', []):
            st.warning(f"💡 Audit Remark: {err}")
            
        st.markdown("---")
        st.markdown("### Manual Refinement")
        feedback = st.text_area("Provide feedback for regeneration (e.g., 'Add a field for smoker status')", value=st.session_state.review_feedback)
        
        if st.button("🔄 Trigger Smart Regeneration"):
            st.session_state.review_feedback = feedback
            # To implement regeneration, we inject the feedback into the state and re-run designer
            app = create_graph()
            
            # We "resume" by creating a state that has the previous errors/context + feedback
            # Ensure errors list is copied correctly
            current_errors = list(st.session_state.final_state.get('errors', []))
            current_errors.append(f"USER FEEDBACK: {feedback}")
            
            resume_data = st.session_state.final_state.copy()
            resume_data['errors'] = current_errors
            resume_data['is_valid'] = False # Force designer to run
            
            resume_state = AgentState(**resume_data)
            
            with st.status("🛠️ Regenerating based on feedback...", expanded=True) as status:
                # We start directly at designer by using update_state or just re-running the graph
                # For simplicity, we re-run from the analyzer to ensure context is fresh
                for event in app.stream(resume_state):
                    for node_name, state_update in event.items():
                        st.write(f"✅ Node: **{node_name.title()}**")
                        st.session_state.final_state = state_update
            st.rerun()
    else:
        st.info("Run the collaboration loop first to enable the Review tab.")

st.markdown('---')
st.caption('Architecture: LangGraph + Gemini 2.5 Flash + Ollama (Nomic-Embed) + Qdrant (Docker) + Pydantic')

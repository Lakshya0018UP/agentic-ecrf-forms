from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class eCRFField(BaseModel):
    field_id: str
    label: str
    data_type: str
    control_type: str
    required: bool
    codelist: Optional[List[Dict[str, str]]] = None
    protocol_specific: bool = False

class eCRFForm(BaseModel):
    form_id: str
    form_name: str
    domain: str
    fields: List[eCRFField]
    is_log_form: bool = False
    applicable_visits: List[str] = []

class AgentState(BaseModel):
    """The Shared Memory of the LangGraph"""
    protocol_path: str = ""
    target_domains: List[str] = []
    current_domain: str = ""
    extracted_context: str = ""
    protocol_summary: str = ""
    study_info: Dict = {}
    visit_schedule: List[Dict] = []
    assessment_map: Dict = {}
    extraction_notes: List[str] = []
    draft_form: Optional[eCRFForm] = None
    final_forms: List[eCRFForm] = []
    errors: List[str] = []
    is_valid: bool = False
    iterations: int = 0

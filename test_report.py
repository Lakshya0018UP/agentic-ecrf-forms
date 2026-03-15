from src.utils.report_generator import generate_docx_report
from src.utils.state import eCRFForm, eCRFField

def test_report_generation():
    test_field = eCRFField(
        field_id="VSORRES",
        label="Vital Signs Result",
        data_type="Numeric",
        control_type="Text Box",
        required=True,
        protocol_specific=True
    )
    
    test_form = eCRFForm(
        form_id="VS",
        form_name="Vital Signs",
        domain="VS",
        fields=[test_field],
        is_log_form=True
    )
    
    filename = "test_report.docx"
    generate_docx_report([test_form], filename)
    print(f"Test report generated: {filename}")

if __name__ == "__main__":
    test_report_generation()

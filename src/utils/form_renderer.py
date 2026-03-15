from typing import Dict, List
from src.utils.state import eCRFForm, eCRFField

def render_form_html(form: eCRFForm) -> str:
    """Generates a professional HTML/CSS representation of the eCRF form."""
    
    html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 800px; margin: auto; padding: 20px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e0e0e0;">
        <div style="border-bottom: 2px solid #004a99; padding-bottom: 10px; margin-bottom: 20px;">
            <h2 style="color: #004a99; margin: 0;">{form.form_name}</h2>
            <p style="color: #666; margin: 5px 0 0 0;">Domain: <strong>{form.domain}</strong> | Form ID: <strong>{form.form_id}</strong></p>
        </div>
        
        <form style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
    """
    
    for field in form.fields:
        # Check if it should be a full-width field
        grid_col = "span 2" if len(field.label) > 40 or field.control_type == "textarea" else "span 1"
        
        html += f"""
        <div style="grid-column: {grid_col}; display: flex; flex-direction: column;">
            <label style="font-weight: 600; margin-bottom: 5px; color: #333; font-size: 0.9rem;">
                {field.label} {"<span style='color: red;'>*</span>" if field.required else ""}
            </label>
        """
        
        if field.codelist:
            # Helper to extract code and label from codelist items safely
            def get_item_data(item):
                if isinstance(item, dict):
                    c = item.get("code", item.get("value", str(item)))
                    l = item.get("label", item.get("display", c))
                    return c, l
                return str(item), str(item)

            if field.control_type.lower() == "radio":
                html += '<div style="display: flex; flex-direction: column; gap: 5px; margin-top: 5px;">'
                for item in field.codelist:
                    c, l = get_item_data(item)
                    html += f"""
                    <label style="font-weight: normal; font-size: 0.85rem; display: flex; align-items: center; gap: 8px; cursor: pointer;">
                        <input type="radio" name="{field.field_id}" value="{c}" style="cursor: pointer;">
                        {l}
                    </label>
                    """
                html += '</div>'
            elif field.control_type.lower() == "checkbox":
                html += '<div style="display: flex; flex-direction: column; gap: 5px; margin-top: 5px;">'
                for item in field.codelist:
                    c, l = get_item_data(item)
                    html += f"""
                    <label style="font-weight: normal; font-size: 0.85rem; display: flex; align-items: center; gap: 8px; cursor: pointer;">
                        <input type="checkbox" name="{field.field_id}" value="{c}" style="cursor: pointer;">
                        {l}
                    </label>
                    """
                html += '</div>'
            else:
                # Default to select for codelists
                html += f"""
                <select style="padding: 8px; border: 1px solid #ccc; border-radius: 4px; background-color: #f9f9f9; font-size: 0.9rem; cursor: pointer;">
                    <option value="">-- Select --</option>
                """
                for item in field.codelist:
                    c, l = get_item_data(item)
                    html += f'<option value="{c}">{l}</option>'
                html += "</select>"
        
        elif field.control_type.lower() == "datepicker" or "date" in field.label.lower():
            html += f'<input type="date" style="padding: 8px; border: 1px solid #ccc; border-radius: 4px; background-color: #f9f9f9; font-size: 0.9rem;">'
        
        elif field.control_type.lower() == "textarea":
            html += f'<textarea rows="3" style="padding: 8px; border: 1px solid #ccc; border-radius: 4px; background-color: #f9f9f9; font-size: 0.9rem; resize: vertical;"></textarea>'
        
        else:
            # Default to text input
            html += f'<input type="text" placeholder="Enter {field.label}..." style="padding: 8px; border: 1px solid #ccc; border-radius: 4px; background-color: #f9f9f9; font-size: 0.9rem;">'
            
        html += f"""
            <span style="font-size: 0.7rem; color: #888; margin-top: 2px;">ID: {field.field_id} | {field.data_type}</span>
        </div>
        """
        
    html += """
        </form>
        <div style="margin-top: 30px; display: flex; justify-content: flex-end;">
            <button type="button" style="padding: 10px 20px; background-color: #004a99; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; opacity: 0.6;" disabled>
                Submit Data (Preview Only)
            </button>
        </div>
    </div>
    """
    
    return html

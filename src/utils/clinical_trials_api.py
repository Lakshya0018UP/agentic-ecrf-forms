import requests
import json

def fetch_clinical_trial_data(nct_id: str):
    """
    Fetches study details from ClinicalTrials.gov API v2.
    Returns a dictionary with consolidated protocol text.
    """
    base_url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
    params = {
        "fields": "protocolSection.identificationModule,protocolSection.descriptionModule,protocolSection.designModule,protocolSection.armsInterventionsModule,protocolSection.outcomesModule,protocolSection.conditionsModule"
    }
    
    try:
        print(f"Requesting data for {nct_id}...")
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        protocol_section = data.get("protocolSection", {})
        
        # 1. Extraction with Fallbacks
        id_mod = protocol_section.get("identificationModule", {})
        desc_mod = protocol_section.get("descriptionModule", {})
        design_mod = protocol_section.get("designModule", {})
        cond_mod = protocol_section.get("conditionsModule", {})
        
        title = id_mod.get("officialTitle") or id_mod.get("briefTitle") or "N/A"
        protocol_num = id_mod.get("orgStudyIdInfo", {}).get("id") or nct_id
        indication = ", ".join(cond_mod.get("conditions", [])) or "N/A"
        phase = ", ".join(design_mod.get("phases", [])) or "N/A"
        
        brief_summary = desc_mod.get("briefSummary", "")
        detailed_description = desc_mod.get("detailedDescription", "")
        
        consolidated_text = f"""
        STUDY METADATA:
        Official Title: {title}
        Protocol Number: {protocol_num}
        NCT ID: {nct_id}
        Indication: {indication}
        Phase: {phase}
        
        BRIEF SUMMARY:
        {brief_summary}
        
        DETAILED DESCRIPTION:
        {detailed_description}
        
        DESIGN DETAILS:
        {json.dumps(design_mod, indent=2)}
        
        ARMS AND INTERVENTIONS:
        {json.dumps(protocol_section.get("armsInterventionsModule", {}), indent=2)}
        """
        
        print(f"Successfully processed {nct_id}")
        return {
            "nct_id": nct_id,
            "title": title,
            "protocol_number": protocol_num,
            "indication": indication,
            "phase": phase,
            "full_text": consolidated_text,
            "raw_data": data
        }
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        return {"error": f"API Error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        print(f"General API Error: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Quick test
    test_id = "NCT04000165"
    result = fetch_clinical_trial_data(test_id)
    if "error" not in result:
        print(f"Successfully fetched: {result['title']}")
        print(f"Text length: {len(result['full_text'])}")
    else:
        print(f"Error: {result['error']}")

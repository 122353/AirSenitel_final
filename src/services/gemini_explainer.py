import os

def explain_case(case: dict) -> tuple[str, str]:
    gemini_enabled = os.environ.get("GEMINI_ENABLED", "false").lower() == "true"
    
    if gemini_enabled:
        # In a real scenario, this would call the Gemini API
        explanation = f"Based on analysis of case {case.get('case_id')}, the anomaly involves a {case.get('case_category', 'general')} event with observed PM2.5 of {case.get('observed_pm25')}. The predicted value was {case.get('predicted_pm25')}. (Note: This is an objective analysis and does not constitute an official AQI reading or health advice)."
        return explanation, "gemini"
    else:
        explanation = f"Automated explanation for case {case.get('case_id')}. Anomaly category: {case.get('case_category', 'Unknown')}. Observed: {case.get('observed_pm25')}, Predicted: {case.get('predicted_pm25')}."
        return explanation, "template"

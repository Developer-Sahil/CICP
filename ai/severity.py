import google.generativeai as genai
import config

genai.configure(api_key=config.GEMINI_API_KEY)

def detect_severity(complaint_text):
    """
    Detect severity level of a complaint using AI.
    
    Args:
        complaint_text (str): The complaint text
        
    Returns:
        str: 'low', 'medium', or 'high'
    """
    try:
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        prompt = f"""Analyze this campus complaint and determine its severity level.

Severity Guidelines:
- HIGH: Health/safety risks, repeated ignored issues, affects many students, urgent action needed, non-functional essential services
- MEDIUM: Significant inconvenience, needs attention soon, affects daily activities, quality issues
- LOW: Minor issues, suggestions for improvement, aesthetic concerns, non-urgent

Complaint: "{complaint_text}"

Return ONLY one word: low, medium, or high"""

        response = model.generate_content(prompt)
        severity = response.text.strip().lower()
        
        # Validate severity
        if severity not in ['low', 'medium', 'high']:
            return detect_severity_fallback(complaint_text)
        
        return severity
        
    except Exception as e:
        print(f"Error detecting severity: {e}")
        return detect_severity_fallback(complaint_text)


def detect_severity_fallback(complaint_text):
    """
    Fallback keyword-based severity detection if AI fails.
    
    Args:
        complaint_text (str): The complaint text
        
    Returns:
        str: 'low', 'medium', or 'high'
    """
    text_lower = complaint_text.lower()
    
    # Check for high severity keywords
    high_count = sum(1 for keyword in config.SEVERITY_HIGH_KEYWORDS if keyword in text_lower)
    medium_count = sum(1 for keyword in config.SEVERITY_MEDIUM_KEYWORDS if keyword in text_lower)
    
    if high_count >= 2:
        return 'high'
    elif high_count >= 1:
        return 'high'
    elif medium_count >= 2:
        return 'medium'
    elif medium_count >= 1:
        return 'medium'
    else:
        return 'low'


def get_severity_score(severity):
    """
    Convert severity to numerical score for sorting/analysis.
    
    Args:
        severity (str): 'low', 'medium', or 'high'
        
    Returns:
        int: Numerical score (1-3)
    """
    severity_map = {
        'low': 1,
        'medium': 2,
        'high': 3
    }
    return severity_map.get(severity, 2)


def detect_batch_severity(complaint_texts):
    """
    Detect severity for multiple complaints in batch.
    
    Args:
        complaint_texts (list): List of complaint texts
        
    Returns:
        list: List of severity levels
    """
    severities = []
    
    for text in complaint_texts:
        severity = detect_severity(text)
        severities.append(severity)
    
    return severities
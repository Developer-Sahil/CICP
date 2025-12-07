import google.generativeai as genai
import config
import re
import logging

genai.configure(api_key=config.GEMINI_API_KEY)
logger = logging.getLogger(__name__)

def detect_severity(complaint_text):
    """
    Detect severity level of a complaint using multi-layer AI analysis.
    
    Args:
        complaint_text (str): The complaint text
        
    Returns:
        str: 'low', 'medium', or 'high'
    """
    try:
        # First pass: Rule-based critical keyword detection
        critical_severity = detect_critical_keywords(complaint_text)
        if critical_severity == 'high':
            logger.info(f"Critical keywords detected, severity: high")
            return 'high'
        
        # Second pass: Enhanced AI analysis with detailed prompt
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        prompt = f"""You are an expert at assessing the severity of campus complaints for university administration.

Analyze this complaint and determine its severity level based on these STRICT criteria:

**HIGH SEVERITY - CRITICAL/URGENT (Choose if ANY apply):**
- Health emergencies or medical issues (injury, illness, hospitalization, poisoning)
- Safety hazards (fire, electrical, structural damage, violence, assault)
- Immediate danger to students (broken equipment causing harm, unsafe conditions)
- Severe hygiene issues (food contamination, disease outbreak, pest infestation)
- Non-functional essential services (no water, no electricity, no heating/cooling in extreme weather)
- Mental health crises (threats, severe distress)
- Discrimination, harassment, or abuse
- Situations requiring IMMEDIATE action (within hours)
- Repeated ignored complaints that have escalated
- Affects health, safety, or wellbeing of multiple students

**MEDIUM SEVERITY - NEEDS ATTENTION (Choose if ANY apply):**
- Significant service disruptions (intermittent essential services)
- Quality issues affecting daily life (poor food quality, slow internet)
- Maintenance issues causing inconvenience (broken but not dangerous)
- Academic concerns (teaching quality, unfair grading)
- Delayed responses from administration
- Financial/billing issues
- Placement/career service problems
- Situations needing attention within days/weeks
- Affects comfort or convenience of students

**LOW SEVERITY - MINOR/SUGGESTIONS:**
- Minor inconveniences (aesthetic issues, suggestions for improvement)
- Feature requests or enhancements
- General feedback without urgency
- Non-critical suggestions

**CRITICAL ANALYSIS RULES:**
1. Medical/Health keywords = AUTOMATIC HIGH severity
2. Safety/Danger keywords = AUTOMATIC HIGH severity  
3. "Hospitalization", "emergency", "injury" = ALWAYS HIGH
4. Food poisoning, contamination = ALWAYS HIGH
5. When uncertain between two levels, choose the HIGHER severity for safety
6. Consider the IMPACT on student wellbeing, not just the words used

Complaint: "{complaint_text}"

Think step by step:
1. Does this involve health/safety? (If YES -> HIGH)
2. Does this involve danger or emergency? (If YES -> HIGH)
3. Does this require immediate action? (If YES -> HIGH)
4. Is this causing significant disruption? (If YES -> MEDIUM)
5. Otherwise -> LOW

Return ONLY one word: high, medium, or low"""

        response = model.generate_content(prompt)
        severity = response.text.strip().lower()
        
        # Validate and clean response
        severity = extract_severity_from_response(severity)
        
        # Third pass: Verify AI decision with scoring system
        verification_score = calculate_severity_score(complaint_text)
        
        # Override AI if verification indicates higher severity
        if verification_score >= 8 and severity != 'high':
            logger.warning(f"Severity override: AI said '{severity}' but score is {verification_score}, changing to 'high'")
            severity = 'high'
        elif verification_score >= 5 and severity == 'low':
            logger.warning(f"Severity override: AI said '{severity}' but score is {verification_score}, changing to 'medium'")
            severity = 'medium'
        
        logger.info(f"Final severity: {severity} (verification score: {verification_score})")
        return severity
        
    except Exception as e:
        logger.error(f"Error detecting severity with AI: {e}")
        # Fallback to enhanced keyword-based detection
        return detect_severity_enhanced_fallback(complaint_text)


def detect_critical_keywords(complaint_text):
    """
    Critical keyword detection - immediately return HIGH for certain terms.
    
    Args:
        complaint_text (str): The complaint text
        
    Returns:
        str: 'high' if critical keywords found, otherwise None
    """
    text_lower = complaint_text.lower()
    
    # CRITICAL keywords that should ALWAYS be high severity
    critical_terms = [
        # Medical emergencies
        'hospital', 'hospitalized', 'hospitalization', 'admitted to hospital',
        'emergency room', 'er visit', 'ambulance', 'medical emergency',
        'severe injury', 'injured badly', 'broken bone', 'fracture',
        'bleeding', 'blood', 'unconscious', 'fainted', 'collapsed',
        'poisoning', 'poison', 'food poisoning', 'sick multiple students',
        'vomiting', 'severe pain', 'chest pain', 'difficulty breathing',
        'allergic reaction', 'anaphylaxis', 'seizure', 'stroke',
        
        # Safety hazards
        'fire', 'electrical shock', 'electrocuted', 'gas leak',
        'carbon monoxide', 'structural damage', 'building collapse',
        'ceiling falling', 'wall crack', 'unsafe building',
        
        # Violence and threats
        'assault', 'attacked', 'violence', 'threat', 'threatened',
        'harassment', 'sexual harassment', 'abuse', 'molested',
        
        # Severe contamination
        'contaminated food', 'rotten food', 'maggots in food',
        'rat in food', 'cockroach in food', 'insect in food',
        'moldy food', 'spoiled food', 'food made me sick',
        
        # Critical failures
        'no water for days', 'no electricity for days',
        'no heating in winter', 'no cooling in summer',
        'toilet overflow', 'sewage backup',
        
        # Mental health crises
        'suicidal', 'suicide', 'mental breakdown', 'panic attack',
        'severe anxiety', 'severe depression'
    ]
    
    for term in critical_terms:
        if term in text_lower:
            logger.info(f"Critical keyword detected: '{term}'")
            return 'high'
    
    # Check for medical facility mentions
    medical_facilities = ['hospital', 'clinic', 'medical center', 'doctor', 'er', 'emergency']
    urgency_terms = ['urgent', 'emergency', 'critical', 'serious', 'severe', 'immediately']
    
    has_medical = any(term in text_lower for term in medical_facilities)
    has_urgency = any(term in text_lower for term in urgency_terms)
    
    if has_medical and has_urgency:
        logger.info("Medical + urgency combination detected")
        return 'high'
    
    return None


def calculate_severity_score(complaint_text):
    """
    Calculate numerical severity score (0-10) for verification.
    
    Args:
        complaint_text (str): The complaint text
        
    Returns:
        int: Severity score (0-10)
    """
    text_lower = complaint_text.lower()
    score = 0
    
    # Health impact indicators (3 points each)
    health_terms = ['hospital', 'injury', 'sick', 'ill', 'disease', 'infection', 
                   'pain', 'medical', 'health', 'poisoning', 'vomit', 'fever']
    score += sum(3 for term in health_terms if term in text_lower)
    
    # Safety hazards (4 points each)
    safety_terms = ['danger', 'unsafe', 'hazard', 'fire', 'electrical', 
                   'shock', 'gas', 'toxic', 'collapse', 'falling']
    score += sum(4 for term in safety_terms if term in text_lower)
    
    # Urgency indicators (2 points each)
    urgency_terms = ['urgent', 'emergency', 'immediate', 'critical', 'serious', 
                    'severe', 'asap', 'now', 'today']
    score += sum(2 for term in urgency_terms if term in text_lower)
    
    # Multiple people affected (3 points)
    plural_terms = ['students', 'everyone', 'all of us', 'many people', 'several', 
                   'multiple', 'whole floor', 'entire']
    if any(term in text_lower for term in plural_terms):
        score += 3
    
    # Repeated issues (2 points)
    repeated_terms = ['again', 'still', 'continue', 'repeated', 'multiple times', 
                     'many times', 'keep', 'ongoing']
    if any(term in text_lower for term in repeated_terms):
        score += 2
    
    # Ignored complaints (2 points)
    ignored_terms = ['ignored', 'no response', 'didn\'t respond', 'not addressed', 
                    'no action', 'nothing done']
    if any(term in text_lower for term in ignored_terms):
        score += 2
    
    # Time sensitivity (2 points)
    time_terms = ['days', 'weeks', 'month', 'long time', 'since']
    if any(term in text_lower for term in time_terms):
        score += 2
    
    # Essential services (3 points)
    essential_terms = ['water', 'electricity', 'power', 'heating', 'cooling', 
                      'wifi', 'internet', 'food', 'bathroom', 'toilet']
    non_functional = ['not working', 'broken', 'no', 'without', 'stopped', 'failed']
    
    has_essential = any(term in text_lower for term in essential_terms)
    has_failure = any(term in text_lower for term in non_functional)
    
    if has_essential and has_failure:
        score += 3
    
    # Cap score at 10
    return min(score, 10)


def extract_severity_from_response(response_text):
    """
    Extract severity level from AI response text.
    
    Args:
        response_text (str): AI response text
        
    Returns:
        str: 'low', 'medium', or 'high'
    """
    text_lower = response_text.lower()
    
    # Look for severity levels in response
    if 'high' in text_lower:
        return 'high'
    elif 'medium' in text_lower:
        return 'medium'
    elif 'low' in text_lower:
        return 'low'
    
    # If response is unclear, default to medium for safety
    logger.warning(f"Could not extract clear severity from response: {response_text}")
    return 'medium'


def detect_severity_enhanced_fallback(complaint_text):
    """
    Enhanced fallback keyword-based severity detection if AI fails.
    
    Args:
        complaint_text (str): The complaint text
        
    Returns:
        str: 'low', 'medium', or 'high'
    """
    text_lower = complaint_text.lower()
    
    # Check critical keywords first
    critical = detect_critical_keywords(text_lower)
    if critical:
        return critical
    
    # Calculate score
    score = calculate_severity_score(text_lower)
    
    # Map score to severity
    if score >= 8:
        return 'high'
    elif score >= 4:
        return 'medium'
    else:
        return 'low'


def detect_severity_fallback(complaint_text):
    """
    Original fallback for backwards compatibility.
    
    Args:
        complaint_text (str): The complaint text
        
    Returns:
        str: 'low', 'medium', or 'high'
    """
    return detect_severity_enhanced_fallback(complaint_text)


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


def explain_severity(complaint_text, severity):
    """
    Provide explanation for severity classification.
    
    Args:
        complaint_text (str): The complaint text
        severity (str): Detected severity level
        
    Returns:
        dict: Explanation with reasons
    """
    text_lower = complaint_text.lower()
    reasons = []
    
    # Check what triggered this severity
    if severity == 'high':
        if any(term in text_lower for term in ['hospital', 'injury', 'emergency']):
            reasons.append("Health/medical emergency detected")
        if any(term in text_lower for term in ['danger', 'unsafe', 'fire', 'hazard']):
            reasons.append("Safety hazard identified")
        if any(term in text_lower for term in ['poison', 'contaminated', 'sick']):
            reasons.append("Health risk to students")
        if calculate_severity_score(text_lower) >= 8:
            reasons.append("High severity score based on multiple factors")
    
    elif severity == 'medium':
        if any(term in text_lower for term in ['problem', 'issue', 'broken']):
            reasons.append("Service disruption or quality issue")
        if any(term in text_lower for term in ['delay', 'slow', 'poor']):
            reasons.append("Performance or quality concerns")
        if calculate_severity_score(text_lower) >= 4:
            reasons.append("Moderate severity score")
    
    else:  # low
        reasons.append("Minor issue or suggestion for improvement")
    
    return {
        'severity': severity,
        'reasons': reasons,
        'score': calculate_severity_score(text_lower)
    }
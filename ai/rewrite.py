import google.generativeai as genai
import config

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)

def rewrite_complaint(raw_text):
    """
    Rewrite a raw student complaint into a formal, well-structured complaint.
    
    Args:
        raw_text (str): Original complaint text from student
        
    Returns:
        str: Rewritten formal complaint
    """
    try:
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        prompt = f"""You are an expert at transforming casual student complaints into formal, professional complaints that will be taken seriously by university administration.

Rewrite this student complaint to be:
- Clear and concise
- Professional and formal in tone
- Impactful and persuasive
- Specific about the issue
- Action-oriented

Original complaint: "{raw_text}"

Rewritten formal complaint:"""

        response = model.generate_content(prompt)
        rewritten = response.text.strip()
        
        return rewritten
        
    except Exception as e:
        print(f"Error rewriting complaint: {e}")
        # Return original if API fails
        return raw_text


def batch_rewrite_complaints(complaints_list):
    """
    Rewrite multiple complaints in batch.
    
    Args:
        complaints_list (list): List of raw complaint texts
        
    Returns:
        list: List of rewritten complaints
    """
    rewritten_list = []
    
    for complaint in complaints_list:
        rewritten = rewrite_complaint(complaint)
        rewritten_list.append(rewritten)
    
    return rewritten_list
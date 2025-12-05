import google.generativeai as genai
import config
import json

genai.configure(api_key=config.GEMINI_API_KEY)

def classify_category(complaint_text):
    """
    Classify complaint into predefined categories using AI.
    
    Args:
        complaint_text (str): The complaint text to classify
        
    Returns:
        str: Category name
    """
    try:
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        categories = [
            'Mess Food Quality',
            'Campus Wi-Fi',
            'Medical Center',
            'Placement/CDC',
            'Faculty Concerns',
            'Hostel Maintenance',
            'Other'
        ]
        
        prompt = f"""Classify this campus complaint into ONE of the following categories:

Categories:
{', '.join(categories)}

Complaint: "{complaint_text}"

Return ONLY the category name, nothing else."""

        response = model.generate_content(prompt)
        category = response.text.strip()
        
        # Validate category
        if category not in categories:
            # Try fuzzy matching
            category_lower = category.lower()
            for cat in categories:
                if cat.lower() in category_lower or category_lower in cat.lower():
                    return cat
            return 'Other'
        
        return category
        
    except Exception as e:
        print(f"Error classifying complaint: {e}")
        return classify_category_fallback(complaint_text)


def classify_category_fallback(complaint_text):
    """
    Fallback keyword-based classification if AI fails.
    
    Args:
        complaint_text (str): The complaint text
        
    Returns:
        str: Category name
    """
    text_lower = complaint_text.lower()
    
    # Check each category's keywords
    for category, keywords in config.CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category
    
    return 'Other'


def classify_batch(complaint_texts):
    """
    Classify multiple complaints in batch.
    
    Args:
        complaint_texts (list): List of complaint texts
        
    Returns:
        list: List of category names
    """
    categories = []
    
    for text in complaint_texts:
        category = classify_category(text)
        categories.append(category)
    
    return categories
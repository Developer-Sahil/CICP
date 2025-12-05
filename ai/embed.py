import google.generativeai as genai
import numpy as np
import config

genai.configure(api_key=config.GEMINI_API_KEY)

def generate_embedding(text):
    """
    Generate embedding vector for text using Gemini API.
    
    Args:
        text (str): Text to generate embedding for
        
    Returns:
        numpy.ndarray: Embedding vector
    """
    try:
        result = genai.embed_content(
            model=config.GEMINI_EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_document"
        )
        
        embedding = np.array(result['embedding'])
        return embedding
        
    except Exception as e:
        print(f"Error generating embedding: {e}")
        # Return zero vector if API fails
        return np.zeros(config.EMBEDDING_DIMENSION)


def generate_batch_embeddings(texts):
    """
    Generate embeddings for multiple texts.
    
    Args:
        texts (list): List of texts
        
    Returns:
        list: List of embedding vectors
    """
    embeddings = []
    
    for text in texts:
        embedding = generate_embedding(text)
        embeddings.append(embedding)
    
    return embeddings


def cosine_similarity(embedding1, embedding2):
    """
    Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1 (numpy.ndarray): First embedding vector
        embedding2 (numpy.ndarray): Second embedding vector
        
    Returns:
        float: Cosine similarity score (0-1)
    """
    if embedding1 is None or embedding2 is None:
        return 0.0
    
    # Normalize vectors
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    # Calculate cosine similarity
    similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
    
    return float(similarity)


def find_similar_complaints(target_embedding, all_embeddings, threshold=None):
    """
    Find complaints similar to target based on embedding similarity.
    
    Args:
        target_embedding (numpy.ndarray): Target embedding vector
        all_embeddings (list): List of (id, embedding) tuples
        threshold (float): Similarity threshold (default from config)
        
    Returns:
        list: List of (id, similarity_score) tuples
    """
    if threshold is None:
        threshold = config.SIMILARITY_THRESHOLD
    
    similar = []
    
    for complaint_id, embedding in all_embeddings:
        if embedding is None:
            continue
            
        similarity = cosine_similarity(target_embedding, embedding)
        
        if similarity >= threshold:
            similar.append((complaint_id, similarity))
    
    # Sort by similarity descending
    similar.sort(key=lambda x: x[1], reverse=True)
    
    return similar
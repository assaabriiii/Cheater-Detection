from sentence_transformers import SentenceTransformer, util

# Initialize the model once
model = SentenceTransformer('all-MiniLM-L6-v2')

def check_similarity(text1, text2):
    """
    Check the similarity between two texts using sentence transformers.
    
    Args:
        text1 (str): First text to compare
        text2 (str): Second text to compare
        
    Returns:
        float: Similarity score between 0 and 1
    """
    try:
        embeddings = model.encode([text1, text2])
        similarity = util.cos_sim(embeddings[0], embeddings[1]).item()
        print(similarity)
        return similarity
    except Exception as e:
        print(f"Error calculating similarity: {e}")
        print(similarity)
        return 0.0

# Example usage
if __name__ == "__main__":
    text1 = "The quick brown fox jumps over the lazy dog."
    text2 = "A fast, dark-colored fox leaps above a sleepy canine."
    similarity = check_similarity(text1, text2)
    print(f"Similarity: {similarity:.2f}")  # Outputs ~0.85 (paraphrased)
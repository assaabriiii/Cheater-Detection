import json
import numpy as np
import difflib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os

# Constants
MIN_MATCH_LEN = 5           
SIMILARITY_THRESHOLD = 0.5  
COSINE_THRESHOLD = 0.8      
MIN_SUSPICIOUS_QUESTIONS = 2  
TIME_CORR_THRESHOLD = 0.7  

def detect_cheaters():
    """Detect pairs of students with suspicious similarities in answers and time taken."""
    # Define the path to results.json relative to the current file
    file_path = os.path.join(os.path.dirname(__file__), '../results.json')
    
    # Load the results data
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []  # Return empty list if file is missing or corrupted

    # Extract students and question numbers
    students = list(data.keys())
    if len(students) < 2:
        return []  # Need at least two students to compare
    
    question_numbers = sorted(set(q['qnumber'] for student in data for q in data[student]))
    
    # Organize answers and times by question and student
    answers = {
        qnum: {
            student: next((q['description'] for q in data[student] if q['qnumber'] == qnum), "")
            for student in students
        } for qnum in question_numbers
    }
    times = {
        qnum: {
            student: next((q['time_taken'] for q in data[student] if q['qnumber'] == qnum), 0)
            for student in students
        } for qnum in question_numbers
    }

    # Compute time correlation matrix
    time_matrix = np.array([[times[qnum][student] for qnum in question_numbers] for student in students])
    time_correlation_matrix = np.corrcoef(time_matrix)

    # Detect suspicious pairs
    suspicious_pairs = []
    tfidf = TfidfVectorizer()
    for i in range(len(students)):
        for j in range(i + 1, len(students)):
            student1, student2 = students[i], students[j]
            suspicious_questions = []
            for qnum in question_numbers:
                ans1 = answers[qnum][student1].strip()
                ans2 = answers[qnum][student2].strip()
                
                if not ans1 or not ans2:
                    continue
                
                # Difflib similarity
                matcher = difflib.SequenceMatcher(None, ans1, ans2)
                matching_blocks = [block for block in matcher.get_matching_blocks() if block.size >= MIN_MATCH_LEN]
                total_matching_length = sum(block.size for block in matching_blocks)
                diff_similarity = total_matching_length / max(len(ans1), len(ans2)) if max(len(ans1), len(ans2)) > 0 else 0
                
                # Cosine similarity
                tfidf_matrix = tfidf.fit_transform([ans1, ans2])
                cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                
                # Mark question as suspicious if thresholds are exceeded
                if diff_similarity > SIMILARITY_THRESHOLD or cosine_sim > COSINE_THRESHOLD:
                    suspicious_questions.append({
                        'qnumber': qnum,
                        'answer1': ans1,
                        'answer2': ans2,
                        'matching_blocks': matching_blocks,
                        'diff_similarity': diff_similarity,
                        'cosine_similarity': cosine_sim
                    })
            
            # Check if pair is suspicious based on number of questions and time correlation
            if len(suspicious_questions) >= MIN_SUSPICIOUS_QUESTIONS:
                time_corr = time_correlation_matrix[i, j]
                if time_corr > TIME_CORR_THRESHOLD:
                    avg_diff_sim = np.mean([q['diff_similarity'] for q in suspicious_questions])
                    avg_cosine_sim = np.mean([q['cosine_similarity'] for q in suspicious_questions])
                    suspicious_pairs.append({
                        'pair': (student1, student2),
                        'suspicious_questions': suspicious_questions,
                        'avg_diff_similarity': avg_diff_sim,
                        'avg_cosine_similarity': avg_cosine_sim,
                        'time_corr': time_corr
                    })
    
    return suspicious_pairs
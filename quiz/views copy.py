import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Question
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import difflib

def welcome(request):
    if request.method == 'POST':
        request.session['student_name'] = request.POST['name']
        return redirect('quiz')
    return render(request, 'quiz/welcome.html')

def quiz(request):
    questions = Question.objects.all().order_by('number')
    student_name = request.session.get('student_name')
    if not student_name:
        return redirect('welcome')
    
    return render(request, 'quiz/quiz.html', {
        'student_name': student_name,
        'total_questions': questions.count()
    })

@csrf_exempt
def get_question(request):
    if request.method == 'POST':
        question_number = int(request.POST.get('question_number'))
        try:
            question = Question.objects.get(number=question_number)
            return JsonResponse({
                'success': True,
                'question': question.text,
                'number': question.number
            })
        except Question.DoesNotExist:
            return JsonResponse({'success': False})

@csrf_exempt
def save_answer(request):
    if request.method == 'POST':
        student_name = request.session.get('student_name')
        data = json.loads(request.body)
        answer = {
            'qnumber': data['qnumber'],
            'description': data['answer'],
            'time_taken': data['time_taken']
        }
        
        # Load existing data or create new
        file_path = os.path.join(os.path.dirname(__file__), '../results.json')
        try:
            with open(file_path, 'r') as f:
                results = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            results = {}

        # Add student's answer
        if student_name not in results:
            results[student_name] = []
        results[student_name].append(answer)

        # Save to file
        with open(file_path, 'w') as f:
            json.dump(results, f, indent=2)

        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def show_cheaters(request):
    # Constants for cheating detection - adjusted for more sensitive detection
    MIN_MATCH_LEN = 5
    SIMILARITY_THRESHOLD = 0.3  # Lowered from 0.5
    COSINE_THRESHOLD = 0.6     # Lowered from 0.8
    MIN_SUSPICIOUS_QUESTIONS = 2
    TIME_CORR_THRESHOLD = 0.5  # Lowered from 0.7

    # Load results data
    file_path = os.path.join(os.path.dirname(__file__), '../results.json')
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return render(request, 'quiz/cheaters.html', {'error': 'No results data found'})

    students = list(data.keys())
    if len(students) < 2:
        return render(request, 'quiz/cheaters.html', {'error': 'Not enough submissions to analyze'})

    # Get latest answer for each question (in case of multiple submissions)
    def get_latest_answer(student_answers, qnum):
        matching_answers = [a for a in student_answers if a['qnumber'] == qnum]
        return matching_answers[-1] if matching_answers else None

    question_numbers = sorted(set(q['qnumber'] for student in data for q in data[student]))
    answers = {qnum: {student: get_latest_answer(data[student], qnum)['description']
                     for student in students
                     if get_latest_answer(data[student], qnum)} 
              for qnum in question_numbers}
    times = {qnum: {student: get_latest_answer(data[student], qnum)['time_taken']
                   for student in students
                   if get_latest_answer(data[student], qnum)}
            for qnum in question_numbers}

    time_matrix = np.array([[times[qnum][student] for qnum in question_numbers] for student in students])
    time_correlation_matrix = np.corrcoef(time_matrix)

    suspicious_pairs = []
    tfidf = TfidfVectorizer(ngram_range=(1, 3))  # Added n-grams for better phrase detection

    for i in range(len(students)):
        for j in range(i + 1, len(students)):
            student1, student2 = students[i], students[j]
            suspicious_questions = []
            
            for qnum in question_numbers:
                ans1 = answers[qnum][student1].strip()
                ans2 = answers[qnum][student2].strip()
                
                # Check for common phrases
                matcher = difflib.SequenceMatcher(None, ans1, ans2)
                matching_blocks = [block for block in matcher.get_matching_blocks() if block.size >= MIN_MATCH_LEN]
                total_matching_length = sum(block.size for block in matching_blocks)
                diff_similarity = total_matching_length / max(len(ans1), len(ans2)) if max(len(ans1), len(ans2)) > 0 else 0

                try:
                    # Improved text similarity analysis
                    tfidf_matrix = tfidf.fit_transform([ans1, ans2])
                    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                except:
                    cosine_sim = 0

                # Store matching phrases for visualization
                matching_phrases = []
                for block in matching_blocks:
                    if block.size >= MIN_MATCH_LEN:
                        phrase = ans1[block.a:block.a + block.size]
                        if len(phrase.split()) >= 2:  # Only include phrases with 2+ words
                            matching_phrases.append(phrase)

                if diff_similarity > SIMILARITY_THRESHOLD or cosine_sim > COSINE_THRESHOLD:
                    suspicious_questions.append({
                        'qnumber': qnum,
                        'answer1': ans1,
                        'answer2': ans2,
                        'diff_similarity': diff_similarity,
                        'cosine_similarity': cosine_sim,
                        'matching_phrases': matching_phrases
                    })
            
            if len(suspicious_questions) >= MIN_SUSPICIOUS_QUESTIONS:
                time_corr = time_correlation_matrix[i, j]
                if time_corr > TIME_CORR_THRESHOLD:
                    avg_diff_sim = np.mean([q['diff_similarity'] for q in suspicious_questions])
                    avg_cosine_sim = np.mean([q['cosine_similarity'] for q in suspicious_questions])
                    suspicious_pairs.append({
                        'student1': student1,
                        'student2': student2,
                        'suspicious_questions': suspicious_questions,
                        'avg_diff_similarity': avg_diff_sim,
                        'avg_cosine_similarity': avg_cosine_sim,
                        'time_correlation': time_corr,
                        'severity': 'high' if (avg_diff_sim > 0.7 or avg_cosine_sim > 0.8) else 'medium'
                    })

    # Sort suspicious pairs by severity and similarity scores
    suspicious_pairs.sort(key=lambda x: (
        x['severity'] == 'high',
        x['avg_cosine_similarity'] + x['avg_diff_similarity']
    ), reverse=True)

    return render(request, 'quiz/cheaters.html', {
        'suspicious_pairs': suspicious_pairs
    })
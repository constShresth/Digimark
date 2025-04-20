from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import os
import json
import pandas as pd
from datetime import datetime
import uuid

# Import custom modules
from modules.ocr_engine import OCREngine
from modules.evaluation_engine import EvaluationEngine
from modules.analytics_engine import AnalyticsEngine
from modules.report_generator import ReportGenerator

app = Flask(__name__)
app.secret_key = 'digital_marking_secret_key'

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'txt'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload directories if they don't exist
os.makedirs(os.path.join(UPLOAD_FOLDER, 'answer_sheets'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'answer_keys'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'results'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'reports'), exist_ok=True)

# Initialize engines
ocr_engine = OCREngine(languages='eng')
evaluation_engine = EvaluationEngine()
analytics_engine = AnalyticsEngine()
report_generator = ReportGenerator(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Check if the post request has the file parts
        if 'answer_sheet' not in request.files or 'answer_key' not in request.files:
            flash('Missing file part', 'error')
            return redirect(request.url)
        
        answer_sheet = request.files['answer_sheet']
        answer_key = request.files['answer_key']
        
        # If user does not select files, browser submits empty files without filenames
        if answer_sheet.filename == '' or answer_key.filename == '':
            flash('No selected files', 'error')
            return redirect(request.url)
        
        # Get form data
        student_name = request.form.get('student_name', 'Unknown')
        student_id = request.form.get('student_id', 'Unknown')
        exam_title = request.form.get('exam_title', 'Exam')
        num_questions = int(request.form.get('num_questions', 5))
        
        # Check if files are allowed
        if not (allowed_file(answer_sheet.filename) and allowed_file(answer_key.filename)):
            flash('File type not allowed', 'error')
            return redirect(request.url)
        
        # Generate unique filenames
        answer_sheet_filename = secure_filename(f"{uuid.uuid4()}_{answer_sheet.filename}")
        answer_key_filename = secure_filename(f"{uuid.uuid4()}_{answer_key.filename}")
        
        # Save files
        answer_sheet_path = os.path.join(UPLOAD_FOLDER, 'answer_sheets', answer_sheet_filename)
        answer_key_path = os.path.join(UPLOAD_FOLDER, 'answer_keys', answer_key_filename)
        
        answer_sheet.save(answer_sheet_path)
        answer_key.save(answer_key_path)
        
        # Process answer key
        model_answers = {}
        
        # Handle different answer key formats
        if answer_key_filename.endswith('.txt'):
            # Parse text file format
            with open(answer_key_path, 'r') as f:
                lines = f.readlines()
                
                current_question = None
                current_answer = []
                current_keywords = []
                current_max_score = 0
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('Q'):
                        # Save previous question if exists
                        if current_question:
                            model_answers[current_question] = {
                                'answer': ' '.join(current_answer),
                                'keywords': current_keywords,
                                'max_score': current_max_score
                            }
                        
                        # Start new question
                        parts = line.split(':')
                        current_question = parts[0].strip()
                        current_answer = []
                        current_keywords = []
                        current_max_score = 0
                    elif line.startswith('A:'):
                        current_answer = [line[2:].strip()]
                    elif line.startswith('K:'):
                        current_keywords = [k.strip() for k in line[2:].split(',')]
                    elif line.startswith('M:'):
                        try:
                            current_max_score = float(line[2:].strip())
                        except ValueError:
                            current_max_score = 10  # Default score
                
                # Save the last question
                if current_question:
                    model_answers[current_question] = {
                        'answer': ' '.join(current_answer),
                        'keywords': current_keywords,
                        'max_score': current_max_score
                    }
        else:
            # Process PDF or image answer key using OCR
            answer_key_text = ocr_engine.process_answer_sheet(answer_key_path, num_questions)
            
            # Create default model answers
            for question_id, text in answer_key_text.items():
                # Extract keywords (simple approach: take important words)
                words = text.split()
                keywords = [word for word in words if len(word) > 4 and word.lower() not in evaluation_engine.stopwords_list]
                keywords = keywords[:min(5, len(keywords))]  # Take up to 5 keywords
                
                model_answers[question_id] = {
                    'answer': text,
                    'keywords': keywords,
                    'max_score': 10  # Default max score
                }
        
        # Process answer sheet
        extracted_texts = ocr_engine.process_answer_sheet(answer_sheet_path, num_questions)
        
        # Evaluate answers
        evaluation_results = {}
        total_score = 0
        max_score = 0
        
        for question_id, text in extracted_texts.items():
            if question_id in model_answers:
                model = model_answers[question_id]
                score, feedback = evaluation_engine.evaluate_answer(
                    text, 
                    model['answer'], 
                    model['keywords'],
                    model['max_score']
                )
                
                matched_keywords, _ = evaluation_engine.keyword_matching(text, model['keywords'])
                
                evaluation_results[question_id] = {
                    'extracted_text': text,
                    'score': score,
                    'max_score': model['max_score'],
                    'feedback': feedback,
                    'matched_keywords': matched_keywords,
                    'keywords': model['keywords']
                }
                
                total_score += score
                max_score += model['max_score']
        
        # Create results dataframe for analytics
        results_df = pd.DataFrame([
            {
                'Question': question_id,
                'Score': result['score'],
                'Max Score': result['max_score'],
                'Percentage': (result['score'] / result['max_score']) * 100 if result['max_score'] > 0 else 0
            }
            for question_id, result in evaluation_results.items()
        ])
        
        # Generate analytics and charts
        charts, performance_metrics = analytics_engine.generate_performance_report(
            results_df, evaluation_results, total_score, max_score
        )
        
        # Generate PDF report
        report_filename = report_generator.generate_pdf_report(
            student_name, student_id, exam_title, results_df, 
            evaluation_results, charts, performance_metrics
        )
        
        # Save evaluation results to JSON file
        result_data = {
            'student_name': student_name,
            'student_id': student_id,
            'exam_title': exam_title,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'evaluation_results': evaluation_results,
            'total_score': total_score,
            'max_score': max_score,
            'percentage': (total_score / max_score * 100) if max_score > 0 else 0,
            'report_filename': report_filename
        }
        
        result_filename = f"result_{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        result_path = os.path.join(UPLOAD_FOLDER, 'results', result_filename)
        
        with open(result_path, 'w') as f:
            json.dump(result_data, f, indent=4)
        
        # Redirect to results page
        return redirect(url_for('results', result_file=result_filename))
    
    return render_template('upload.html')

@app.route('/results/<result_file>')
def results(result_file):
    # Load results from JSON file
    result_path = os.path.join(UPLOAD_FOLDER, 'results', result_file)
    
    if not os.path.exists(result_path):
        flash('Result file not found', 'error')
        return redirect(url_for('index'))
    
    with open(result_path, 'r') as f:
        result_data = json.load(f)
    
    # Create results dataframe for display
    results_df = pd.DataFrame([
        {
            'Question': question_id,
            'Score': result['score'],
            'Max Score': result['max_score'],
            'Percentage': (result['score'] / result['max_score']) * 100 if result['max_score'] > 0 else 0,
            'Feedback': result['feedback']
        }
        for question_id, result in result_data['evaluation_results'].items()
    ])
    
    # Generate charts for display
    charts = {}
    
    # Generate score distribution chart
    charts['score_distribution'] = analytics_engine.generate_score_distribution_chart(results_df)
    
    # Generate keyword chart
    charts['keyword_matching'] = analytics_engine.generate_keyword_chart(result_data['evaluation_results'])
    
    # Generate overall performance chart
    charts['overall_performance'] = analytics_engine.generate_overall_performance_chart(
        result_data['total_score'], result_data['max_score']
    )
    
    return render_template(
        'results.html',
        student_name=result_data['student_name'],
        student_id=result_data['student_id'],
        exam_title=result_data['exam_title'],
        timestamp=result_data['timestamp'],
        total_score=result_data['total_score'],
        max_score=result_data['max_score'],
        percentage=result_data['percentage'],
        results=results_df.to_dict('records'),
        charts=charts,
        report_filename=result_data['report_filename']
    )

@app.route('/download/<filename>')
def download_report(filename):
    return send_from_directory(os.path.join(UPLOAD_FOLDER, 'reports'), filename, as_attachment=True)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)

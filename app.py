from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, Response, send_file
import sqlite3
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from ai import QuestionGenerator
from teacher_backend import TeacherBackend
from enhanced_paper_generation import EnhancedPaperGeneration
from groq import Groq
import markdown
import latex2mathml.converter
from weasyprint import HTML, CSS
from io import BytesIO
import auth  # Import authentication module
from evaluator import Evaluator  # Import evaluator module

app = Flask(__name__)

# Configuration - Session Security
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Database and folder configuration
DATABASE_PATH = 'question_bank.db'
QUESTION_BANK_FOLDER = 'Question Bank'


def login_required(f):
    """Decorator to require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    """Decorator to require teacher role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'teacher':
            flash('Access denied. Teacher privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    """Decorator to require student role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'student':
            flash('Access denied. Student privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def init_database():
    """Initialize the SQLite database with all required tables"""
    try:
        print(f"[INFO] Initializing database at: {DATABASE_PATH}")
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Create teachers table
        print("[INFO] Creating teachers table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teachers (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Create students table
        print("[INFO] Creating students table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

        # Check if the questions table exists and get its schema
        cursor.execute("PRAGMA table_info(questions)")
        columns = [row[1] for row in cursor.fetchall()]

        if not columns:
            # Create new questions table with all columns
            print("[INFO] Creating questions table...")
            cursor.execute('''
                CREATE TABLE questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    subtopic TEXT,
                    difficulty_level TEXT NOT NULL,
                    estimated_time INTEGER NOT NULL,
                    bloom_level TEXT NOT NULL,
                    is_ai_generated BOOLEAN DEFAULT FALSE,
                    ai_generation_notes TEXT,
                    parent_question_id INTEGER,
                    teacher_id TEXT,
                    has_explanation BOOLEAN DEFAULT FALSE,
                    acceptance_status TEXT DEFAULT 'pending',
                    educator_reviewed BOOLEAN DEFAULT FALSE,
                    reviewed_by TEXT,
                    review_timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_question_id) REFERENCES questions (id),
                    FOREIGN KEY (teacher_id) REFERENCES teachers (id)
                )
            ''')
        else:
            # Add missing columns to existing questions table
            print("[INFO] Checking for missing columns in questions table...")
            cursor.execute("PRAGMA table_info(questions)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            new_columns = {
                'is_ai_generated': 'BOOLEAN DEFAULT FALSE',
                'ai_generation_notes': 'TEXT',
                'parent_question_id': 'INTEGER',
                'teacher_id': 'TEXT',
                'has_explanation': 'BOOLEAN DEFAULT FALSE',
                'acceptance_status': "TEXT DEFAULT 'pending'",
                'educator_reviewed': 'BOOLEAN DEFAULT FALSE',
                'reviewed_by': 'TEXT',
                'review_timestamp': 'TIMESTAMP'
            }
            
            for col, definition in new_columns.items():
                if col not in existing_columns:
                    print(f"[INFO] Adding column: {col}")
                    cursor.execute(f'ALTER TABLE questions ADD COLUMN {col} {definition}')

        # Create question_answers table if it doesn't exist
        print("[INFO] Creating question_answers table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                correct_answer TEXT NOT NULL,
                rubric TEXT,
                max_marks REAL DEFAULT 1.0,
                min_marks REAL DEFAULT 0.0,
                max_scored REAL DEFAULT 0.0,
                min_scored REAL DEFAULT 0.0,
                avg_scored REAL DEFAULT 0.0,
                total_attempts INTEGER DEFAULT 0,
                avg_time_taken REAL DEFAULT 0.0,
                FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
            )
        ''')
        
        # Check if rubric column exists in question_answers
        cursor.execute("PRAGMA table_info(question_answers)")
        qa_columns = [row[1] for row in cursor.fetchall()]
        if 'rubric' not in qa_columns:
            print("[INFO] Adding rubric column to question_answers...")
            cursor.execute('ALTER TABLE question_answers ADD COLUMN rubric TEXT')
        
        # Create question_feedback table
        print("[INFO] Creating question_feedback table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                student_id TEXT NOT NULL,
                is_question_clear BOOLEAN,
                is_answer_correct BOOLEAN,
                is_difficulty_appropriate BOOLEAN,
                overall_approval BOOLEAN,
                additional_comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
            )
        ''')
        
        # Create student_submissions table for answer evaluation
        print("[INFO] Creating student_submissions table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                question_id INTEGER NOT NULL,
                submitted_answer TEXT NOT NULL,
                score REAL NOT NULL,
                max_marks REAL NOT NULL,
                time_taken REAL DEFAULT 0,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            )
        ''')

        conn.commit()
        print("[SUCCESS] Database initialized successfully!")
        print(f"[INFO] Database location: {os.path.abspath(DATABASE_PATH)}")
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"[INFO] Created tables: {', '.join(tables)}")
        
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize database: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def create_folder_structure(subject, topic, subtopic=None):
    """Create the folder structure for organizing questions"""
    # Create main Question Bank folder
    base_path = Path(QUESTION_BANK_FOLDER)
    base_path.mkdir(exist_ok=True)

    # Create subject folder
    subject_path = base_path / subject
    subject_path.mkdir(exist_ok=True)

    # Create topic folder
    topic_path = subject_path / topic
    topic_path.mkdir(exist_ok=True)

    # Create subtopic folder if provided
    if subtopic and subtopic.strip():
        subtopic_path = topic_path / subtopic
        subtopic_path.mkdir(exist_ok=True)
        return subtopic_path
    else:
        return topic_path

def save_markdown_file(folder_path, question_id, markdown_content):
    """Save the markdown content to a file"""
    file_path = folder_path / f"{question_id}.md"
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    return str(file_path)

# Question types options
QUESTION_TYPES = [
    'MCQ',
    'Coding',
    'Numerical',
    'Descriptive',
    'Fill-in-the-blank',
    'True/False',
    'Short Answer'
]

# Bloom's Taxonomy levels
BLOOM_LEVELS = [
    'Recall',
    'Understand',
    'Apply',
    'Analyze',
    'Evaluate',
    'Create'
]

# Difficulty levels
DIFFICULTY_LEVELS = [
    'Easy',
    'Medium',
    'Hard'
]


# Initialize Groq client
groq_client = Groq(api_key="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")

@app.route('/')
def index():
    """Main landing page - redirect to login if not logged in"""
    if 'user_id' in session:
        role = session.get('role')
        if role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        elif role == 'student':
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Unified login page for teachers and students"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')  # 'teacher' or 'student'
        
        # Validate inputs
        if not all([username, password, role]):
            flash('Please fill in all fields.', 'danger')
            return render_template('login.html')
        
        if role not in ['teacher', 'student']:
            flash('Invalid role selected.', 'danger')
            return render_template('login.html')
        
        # Authenticate user
        user = auth.authenticate_user(username, password, role)
        
        if user:
            # Set session variables
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            
            # Redirect based on role
            if role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')
    
    # GET request - show login form
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def register():
    """Registration page - redirects to teacher or student registration"""
    role = request.args.get('role', 'teacher')
    if role == 'student':
        return redirect(url_for('register_student'))
    return redirect(url_for('register_teacher'))

@app.route('/register/teacher', methods=['GET', 'POST'])
def register_teacher():
    """Teacher registration page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        
        # Validate inputs
        errors = []
        if not all([username, password, confirm_password, full_name]):
            errors.append('All fields except email are required.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html', role='teacher')
        
        # Create user
        success = auth.create_user(username, password, full_name, email, 'teacher')
        
        if success:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username or email already exists.', 'danger')
            return render_template('register.html', role='teacher')
    
    # GET request - show registration form
    return render_template('register.html', role='teacher')

@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    """Student registration page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        
        # Validate inputs
        errors = []
        if not all([username, password, confirm_password, full_name]):
            errors.append('All fields except email are required.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html', role='student')
        
        # Create user
        success = auth.create_user(username, password, full_name, email, 'student')
        
        if success:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username or email already exists.', 'danger')
            return render_template('register.html', role='student')
    
    # GET request - show registration form
    return render_template('register.html', role='student')

@app.route('/logout')
def logout():
    """Logout user and clear session"""
    username = session.get('full_name', 'User')
    session.clear()
    flash(f'Goodbye, {username}! You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

# ===== Student Answer Evaluation API =====
@app.route('/api/student/submit_answer', methods=['POST'])
@auth.student_required
def submit_student_answer():
    """Evaluate student answer and return score"""
    try:
        data = request.get_json()
        question_id = data.get('question_id')
        student_answer = data.get('student_answer', '').strip()
        student_id = session.get('user_id')
        
        if not question_id or not student_answer:
            return jsonify({'status': 'error', 'error': 'Question ID and answer are required'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Fetch question details
        cursor.execute('''
            SELECT question_type FROM questions WHERE id = ?
        ''', (question_id,))
        
        question_result = cursor.fetchone()
        if not question_result:
            conn.close()
            return jsonify({'status': 'error', 'error': 'Question not found'}), 404
        
        question_type = question_result[0]
        
        # Fetch correct answer/rubric
        cursor.execute('''
            SELECT correct_answer, max_marks FROM question_answers WHERE question_id = ?
        ''', (question_id,))
        
        answer_data = cursor.fetchone()
        if not answer_data:
            conn.close()
            return jsonify({'status': 'error', 'error': 'No answer key available for this question'}), 404
        
        correct_answer = answer_data[0]
        max_marks = float(answer_data[1])
        
        # Evaluate answer using the Evaluator class
        evaluator = Evaluator()
        score = evaluator.evaluate(question_type, student_answer, correct_answer)
        
        # Calculate percentage
        percentage = (score / max_marks * 100) if max_marks > 0 else 0
        
        # Store submission
        cursor.execute('''
            INSERT INTO student_submissions 
            (student_id, question_id, submitted_answer, score, max_marks)
            VALUES (?, ?, ?, ?, ?)
        ''', (student_id, question_id, student_answer, score, max_marks))
        
        # Update question statistics
        cursor.execute('''
            UPDATE question_answers
            SET total_attempts = total_attempts + 1,
                avg_scored = (
                    SELECT AVG(score) 
                    FROM student_submissions 
                    WHERE question_id = ?
                ),
                max_scored = (
                    SELECT MAX(score)
                    FROM student_submissions
                    WHERE question_id = ?
                ),
                min_scored = (
                    SELECT MIN(score)
                    FROM student_submissions
                    WHERE question_id = ?
                )
            WHERE question_id = ?
        ''', (question_id, question_id, question_id, question_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'score': round(score, 2),
            'max_marks': max_marks,
            'percentage': round(percentage, 2),
            'correct_answer': correct_answer,
            'question_type': question_type
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/student/get_explanation/<int:question_id>', methods=['GET'])
@auth.student_required
def get_question_explanation(question_id):
    """Get explanation for a question if it exists"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get question details
        cursor.execute('''
            SELECT subject, topic, subtopic, has_explanation
            FROM questions WHERE id = ?
        ''', (question_id,))
        
        question = cursor.fetchone()
        conn.close()
        
        if not question:
            return jsonify({'status': 'error', 'error': 'Question not found'}), 404
        
        subject, topic, subtopic, has_explanation = question
        
        if not has_explanation:
            return jsonify({'status': 'success', 'has_explanation': False})
        
        # Read explanation file
        folder_path = create_folder_structure(subject, topic, subtopic)
        explanation_file = folder_path / f"{question_id}_explanation.md"
        
        if explanation_file.exists():
            with open(explanation_file, 'r', encoding='utf-8') as f:
                explanation_text = f.read()
            
            return jsonify({
                'status': 'success',
                'has_explanation': True,
                'explanation': explanation_text
            })
        else:
            return jsonify({'status': 'success', 'has_explanation': False})
            
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/teacher/manage_questions')
@auth.teacher_required
def manage_questions():
    """Teacher page to browse and manage question bank"""
    # Get unique values for filters
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get subjects
    cursor.execute('SELECT DISTINCT subject FROM questions ORDER BY subject')
    subjects = [row[0] for row in cursor.fetchall()]
    
    # Get topics
    cursor.execute('SELECT DISTINCT topic FROM questions ORDER BY topic')
    topics = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('manage_questions.html',
                         subjects=subjects,
                         topics=topics,
                         difficulty_levels=DIFFICULTY_LEVELS,
                         bloom_levels=BLOOM_LEVELS,
                         question_types=QUESTION_TYPES)

@app.route('/api/questions/list', methods=['GET'])
@auth.teacher_required
def api_get_questions():
    """API endpoint to get filtered list of questions"""
    # Get filter parameters
    subject = request.args.get('subject')
    topic = request.args.get('topic')
    difficulty = request.args.get('difficulty')
    bloom_level = request.args.get('bloom_level')
    question_type = request.args.get('question_type')
    teacher_id = request.args.get('teacher_id')  # Optional: filter by teacher
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Build query
    query = '''
        SELECT id, title, question_type, subject, topic, difficulty_level, 
               bloom_level, created_at, teacher_id, has_explanation, is_ai_generated
        FROM questions
        WHERE 1=1
    '''
    params = []
    
    if subject:
        query += ' AND subject = ?'
        params.append(subject)
    
    if topic:
        query += ' AND topic = ?'
        params.append(topic)
    
    if difficulty:
        query += ' AND difficulty_level = ?'
        params.append(difficulty)
    
    if bloom_level:
        query += ' AND bloom_level = ?'
        params.append(bloom_level)
    
    if question_type:
        query += ' AND question_type = ?'
        params.append(question_type)
    
    if teacher_id:
        query += ' AND teacher_id = ?'
        params.append(teacher_id)
    
    # Get total count
    count_query = f'SELECT COUNT(*) FROM ({query})'
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]
    
    # Add pagination
    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    
    cursor.execute(query, params)
    questions = cursor.fetchall()
    
    conn.close()
    
    # Format results
    results = []
    for q in questions:
        results.append({
            'id': q[0],
            'title': q[1],
            'question_type': q[2],
            'subject': q[3],
            'topic': q[4],
            'difficulty_level': q[5],
            'bloom_level': q[6],
            'created_at': q[7],
            'teacher_id': q[8],
            'has_explanation': bool(q[9]),
            'is_ai_generated': bool(q[10])
        })
    
    return jsonify({
        'status': 'success',
        'questions': results,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page
    })

@app.route('/api/questions/<int:question_id>/details', methods=['GET'])
@auth.teacher_required
def api_get_question_details(question_id):
    """API endpoint to get full question details including answer, explanation, and stats"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get question details
    cursor.execute('''
        SELECT id, title, question_type, subject, topic, subtopic, difficulty_level,
               estimated_time, bloom_level, has_explanation, is_ai_generated, created_at
        FROM questions
        WHERE id = ?
    ''', (question_id,))
    
    question = cursor.fetchone()
    
    if not question:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Question not found'}), 404
    
    # Get answer/rubric if exists
    cursor.execute('''
        SELECT correct_answer, rubric, max_marks, avg_scored, total_attempts
        FROM question_answers
        WHERE question_id = ?
    ''', (question_id,))
    
    answer_data = cursor.fetchone()
    
    conn.close()
    
    # Read question markdown file
    subject, topic, subtopic = question[3], question[4], question[5]
    folder_path = create_folder_structure(subject, topic, subtopic)
    question_file = folder_path / f"{question_id}.md"
    
    question_text = ""
    if question_file.exists():
        with open(question_file, 'r', encoding='utf-8') as f:
            question_text = f.read()
    
    # Read explanation if exists
    explanation_text = ""
    if question[9]:  # has_explanation
        explanation_file = folder_path / f"{question_id}_explanation.md"
        if explanation_file.exists():
            with open(explanation_file, 'r', encoding='utf-8') as f:
                explanation_text = f.read()
    
    # Build response
    response = {
        'status': 'success',
        'question': {
            'id': question[0],
            'title': question[1],
            'question_type': question[2],
            'subject': question[3],
            'topic': question[4],
            'subtopic': question[5],
            'difficulty_level': question[6],
            'estimated_time': question[7],
            'bloom_level': question[8],
            'has_explanation': bool(question[9]),
            'is_ai_generated': bool(question[10]),
            'created_at': question[11],
            'question_text': question_text,
            'explanation_text': explanation_text
        }
    }
    
    # Add answer/stats if available
    if answer_data:
        response['answer'] = {
            'correct_answer': answer_data[0],
            'rubric': answer_data[1],
            'max_marks': answer_data[2],
            'avg_scored': answer_data[3],
            'total_attempts': answer_data[4]
        }
    
    return jsonify(response)

@app.route('/teacher/edit_explanation/<int:question_id>', methods=['GET', 'POST'])
@auth.teacher_required
def edit_explanation(question_id):
    """Page to add or edit explanation for a question"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get question details
    cursor.execute('''
        SELECT id, title, subject, topic, subtopic, has_explanation
        FROM questions
        WHERE id = ?
    ''', (question_id,))
    
    question = cursor.fetchone()
    
    if not question:
        conn.close()
        flash('Question not found.', 'danger')
        return redirect(url_for('manage_questions'))
    
    # Build folder path
    subject, topic, subtopic = question[2], question[3], question[4]
    folder_path = create_folder_structure(subject, topic, subtopic)
    explanation_file = folder_path / f"{question_id}_explanation.md"
    
    if request.method == 'POST':
        explanation_text = request.form.get('explanation_text', '')
        
        if explanation_text.strip():
            # Save explanation
            with open(explanation_file, 'w', encoding='utf-8') as f:
                f.write(explanation_text)
            
            # Update has_explanation flag
            cursor.execute('''
                UPDATE questions
                SET has_explanation = 1
                WHERE id = ?
            ''', (question_id,))
            conn.commit()
            
            flash('Explanation saved successfully!', 'success')
        else:
            # Delete explanation if empty
            if explanation_file.exists():
                explanation_file.unlink()
            
            # Update has_explanation flag
            cursor.execute('''
                UPDATE questions
                SET has_explanation = 0
                WHERE id = ?
            ''', (question_id,))
            conn.commit()
            
            flash('Explanation removed.', 'info')
        
        conn.close()
        return redirect(url_for('manage_questions'))
    
    # GET request - load existing explanation if any
    explanation_text = ""
    if question[5]:  # has_explanation
        if explanation_file.exists():
            with open(explanation_file, 'r', encoding='utf-8') as f:
                explanation_text = f.read()
    
    conn.close()
    
    return render_template('edit_explanation.html',
                         question_id=question[0],
                         question_title=question[1],
                         explanation_text=explanation_text)


@app.route('/teacher-dashboard')
@teacher_required
def teacher_dashboard():
    """Teacher dashboard with navigation options"""
    return render_template('teacher_dashboard.html', username=session.get('user_id'))

@app.route('/student-dashboard')
@student_required
def student_dashboard():
    """Student dashboard with practice options"""
    return render_template('student_dashboard.html', username=session.get('user_id'))

@app.route('/teacher')
@teacher_required
def teacher():
    return render_template('teacher.html',
                         question_types=QUESTION_TYPES,
                         bloom_levels=BLOOM_LEVELS,
                         difficulty_levels=DIFFICULTY_LEVELS)

@app.route('/teacher/manage')
@teacher_required
def teacher_management():
    """Teacher question management page"""
    return render_template('teacher_management.html')

@app.route('/teacher/review_ai')
@teacher_required
def review_ai_questions_page():
    """Teacher AI question review page"""
    return render_template('teacher_review_ai.html')


@app.route('/create_paper', methods=['GET', 'POST'])
@teacher_required
def create_paper():
    """Paper generation interface"""
    if request.method == 'POST':
        num_questions = request.form.get('num_questions')
        num_papers = request.form.get('num_papers')
        print(f"Number of questions requested: {num_questions}")
        print(f"Number of papers requested: {num_papers}")
        
        # Create folder and empty MD files
        from datetime import datetime
        folder_name = f"paper_set_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        paper_folder = Path('Generated Papers') / folder_name
        paper_folder.mkdir(parents=True, exist_ok=True)
        
        # Create empty MD files for each paper
        for i in range(1, int(num_papers) + 1):
            paper_file = paper_folder / f"paper_{i}.md"
            paper_file.write_text(f"# Paper {i}\n\n")
        
        # Store in session for the next page
        session['num_questions'] = num_questions
        session['num_papers'] = num_papers
        session['paper_folder'] = str(paper_folder)
        session['current_question'] = 1
        
        return jsonify({
            "status": "success", 
            "message": f"Created {num_papers} paper(s) with {num_questions} questions each",
            "redirect": url_for('configure_question')
        })
    
    return render_template('create_paper.html', question_types=QUESTION_TYPES)

@app.route('/configure_question', methods=['GET'])
@teacher_required
def configure_question():
    """Configure individual questions for the paper"""
    current_question = session.get('current_question', 1)
    total_questions = int(session.get('num_questions', 0))
    
    if current_question > total_questions:
        return redirect(url_for('teacher_dashboard'))
    
    # Get available subjects, topics
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT subject FROM questions ORDER BY subject')
    subjects = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('configure_question.html',
                         current_question=current_question,
                         total_questions=total_questions,
                         subjects=subjects,
                         difficulty_levels=DIFFICULTY_LEVELS,
                         bloom_levels=BLOOM_LEVELS,
                         question_types=QUESTION_TYPES)

@app.route('/api/configure/topics', methods=['GET'])
@teacher_required
def get_configure_topics():
    """Get topics for selected subject"""
    subject = request.args.get('subject')
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT topic FROM questions WHERE subject = ? ORDER BY topic', (subject,))
    topics = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({'status': 'success', 'topics': topics})

@app.route('/api/configure/subtopics', methods=['GET'])
@teacher_required
def get_configure_subtopics():
    """Get subtopics for selected subject and topic"""
    subject = request.args.get('subject')
    topic = request.args.get('topic')
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT subtopic FROM questions 
        WHERE subject = ? AND topic = ? AND subtopic IS NOT NULL AND subtopic != ""
        ORDER BY subtopic
    ''', (subject, topic))
    subtopics = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({'status': 'success', 'subtopics': subtopics})

@app.route('/save_question_config', methods=['POST'])
@teacher_required
def save_question_config():
    """Save question configuration and move to next question"""
    data = request.json
    
    current_question = session.get('current_question', 1)
    total_questions = int(session.get('num_questions', 0))
    selected_question_id = data.get('selected_question_id')
    want_ai_question = data.get('want_ai_question', False)
    auto_select = data.get('auto_select', False)
    
    # If auto-select is enabled, randomly select a question matching criteria
    if auto_select and not selected_question_id:
        subject = data.get('subject')
        topic = data.get('topic')
        subtopic = data.get('subtopic')
        difficulty = data.get('difficulty')
        bloom_level = data.get('bloom_level')
        question_type = data.get('question_type')
        
        # Validate required criteria
        if not all([subject, topic, difficulty, bloom_level, question_type]):
            return jsonify({
                'status': 'error',
                'message': 'Subject, topic, difficulty, bloom level, and question type are required for auto-selection'
            }), 400
        
        # Query matching questions with acceptance status filter
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        query = '''
            SELECT id FROM questions
            WHERE subject = ? 
              AND topic = ? 
              AND difficulty_level = ?
              AND bloom_level = ?
              AND question_type = ?
              AND (is_ai_generated = 0 OR acceptance_status = 'accepted')
        '''
        params = [subject, topic, difficulty, bloom_level, question_type]
        
        if subtopic:
            query += ' AND subtopic = ?'
            params.append(subtopic)
        
        cursor.execute(query, params)
        matching_questions = cursor.fetchall()
        conn.close()
        
        if not matching_questions:
            return jsonify({
                'status': 'error',
                'message': 'No questions found matching the specified criteria'
            }), 404
        
        # Randomly select one question
        import random
        selected_question_id = random.choice(matching_questions)[0]
    
    # Validate that a question was selected (either manually or auto)
    if not selected_question_id:
        return jsonify({
            'status': 'error',
            'message': 'Please select a question or enable auto-selection before proceeding'
        }), 400
    
    # Get the question content from database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get all questions including AI variants if requested
    if want_ai_question:
        # Get base question and all its AI variants
        # First check if selected question is AI generated or base
        cursor.execute('SELECT parent_question_id FROM questions WHERE id = ?', (selected_question_id,))
        result = cursor.fetchone()
        parent_id = result[0] if result and result[0] else selected_question_id
        
        # Now get base question and all variants
        cursor.execute('''
            SELECT id, title, question_type, subject, topic, subtopic,
                   difficulty_level, estimated_time, bloom_level
            FROM questions
            WHERE id = ? OR parent_question_id = ?
            ORDER BY is_ai_generated ASC, id ASC
        ''', (parent_id, parent_id))
        
        all_questions = cursor.fetchall()
        
        if not all_questions:
            conn.close()
            return jsonify({
                'status': 'error',
                'message': 'Selected question not found'
            }), 404
        
        print(f"Found {len(all_questions)} question variants (including base)")
    else:
        # Get only the selected question
        cursor.execute('''
            SELECT id, title, question_type, subject, topic, subtopic,
                   difficulty_level, estimated_time, bloom_level
            FROM questions
            WHERE id = ?
        ''', (selected_question_id,))
        
        question_row = cursor.fetchone()
        
        if not question_row:
            conn.close()
            return jsonify({
                'status': 'error',
                'message': 'Selected question not found'
            }), 404
        
        all_questions = [question_row]
    
    # Add question to all paper files
    paper_folder = Path(session.get('paper_folder', 'Generated Papers'))
    num_papers = int(session.get('num_papers', 1))
    
    import random
    
    for i in range(1, num_papers + 1):
        paper_file = paper_folder / f"paper_{i}.md"
        
        if paper_file.exists():
            # Randomly select one question from available variants for this paper
            selected_variant = random.choice(all_questions)
            variant_question_id = selected_variant[0]
            
            # Get the subject, topic, subtopic for folder path
            subject, topic, subtopic = selected_variant[2], selected_variant[3], selected_variant[4]
            
            # Try multiple possible locations for the markdown file
            question_content = ""
            file_found = False
            
            # Location 1: Try the variant's specific folder
            folder_path = create_folder_structure(subject, topic, subtopic)
            question_file_path = folder_path / f"{variant_question_id}.md"
            
            if question_file_path.exists():
                with open(question_file_path, 'r', encoding='utf-8') as f:
                    question_content = f.read()
                print(f"Paper {i}: Found question ID {variant_question_id} at {question_file_path}")
                file_found = True
            else:
                # Location 2: Try without subtopic folder
                folder_path_no_subtopic = create_folder_structure(subject, topic, None)
                question_file_path_alt = folder_path_no_subtopic / f"{variant_question_id}.md"
                
                if question_file_path_alt.exists():
                    with open(question_file_path_alt, 'r', encoding='utf-8') as f:
                        question_content = f.read()
                    print(f"Paper {i}: Found question ID {variant_question_id} at {question_file_path_alt}")
                    file_found = True
                else:
                    # Location 3: Search all possible locations
                    base_path = Path(QUESTION_BANK_FOLDER)
                    for md_file in base_path.rglob(f"{variant_question_id}.md"):
                        with open(md_file, 'r', encoding='utf-8') as f:
                            question_content = f.read()
                        print(f"Paper {i}: Found question ID {variant_question_id} at {md_file}")
                        file_found = True
                        break
            
            if not file_found:
                print(f"WARNING: Question file not found for ID {variant_question_id}")
                print(f"  Tried: {question_file_path}")
                print(f"  Tried: {question_file_path_alt}")
                question_content = f"[Question content not found for ID: {variant_question_id}]\n\nExpected locations:\n- {question_file_path}\n- {question_file_path_alt}"
            
            # Extract Answer component for key Generation
            cursor.execute("SELECT correct_answer, rubric FROM question_answers WHERE question_id = ?", (variant_question_id,))
            answer_rec = cursor.fetchone()
            correct_answer = answer_rec[0] if answer_rec and answer_rec[0] else ""
            rubric = answer_rec[1] if answer_rec and answer_rec[1] else ""
            
            key_block = f"## Question {current_question}\n\n{question_content}\n"
            if correct_answer:
                key_block += f"\n**Formal Answer:**\n{correct_answer}\n"
            if rubric:
                key_block += f"\n**Grading Rubric:**\n{rubric}\n"
            key_block += "\n---\n\n"
            
            # Append only the question content to the paper
            question_block = f"## Question {current_question}\n\n{question_content}\n\n---\n\n"
            
            with open(paper_file, 'a', encoding='utf-8') as f:
                f.write(question_block)
                
            key_file = paper_folder / f"paper_{i}_key.md"
            with open(key_file, 'a', encoding='utf-8') as f:
                if current_question == 1 and not key_file.exists():
                    f.write(f"# Paper {i} - Answer Key\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n")
                f.write(key_block)
    
    conn.close()
    # Move to next question
    session['current_question'] = current_question + 1
    
    if current_question >= total_questions:
        # All questions configured - generate PDFs
        paper_folder = Path(session.get('paper_folder', 'Generated Papers'))
        num_papers = int(session.get('num_papers', 1))
        
        pdf_files = []
        pdf_urls = []
        for i in range(1, num_papers + 1):
            md_file = paper_folder / f"paper_{i}.md"
            pdf_file = paper_folder / f"paper_{i}.pdf"
            key_md_file = paper_folder / f"paper_{i}_key.md"
            key_pdf_file = paper_folder / f"paper_{i}_key.pdf"
            
            if md_file.exists():
                try:
                    # Convert markdown to PDF
                    convert_md_to_pdf(str(md_file), str(pdf_file))
                    pdf_files.append(str(pdf_file))
                    # Create download URL for each PDF
                    pdf_urls.append({
                        'name': f"paper_{i}.pdf",
                        'url': url_for('download_pdf', folder=paper_folder.name, filename=f"paper_{i}.pdf")
                    })
                    print(f"Generated PDF: {pdf_file}")
                except Exception as e:
                    print(f"Error generating PDF for paper {i}: {e}")
                    
            if key_md_file.exists():
                try:
                    convert_md_to_pdf(str(key_md_file), str(key_pdf_file))
                    pdf_files.append(str(key_pdf_file))
                    pdf_urls.append({
                        'name': f"paper_{i}_key.pdf",
                        'url': url_for('download_pdf', folder=paper_folder.name, filename=f"paper_{i}_key.pdf")
                    })
                    print(f"Generated Answer Key PDF: {key_pdf_file}")
                except Exception as e:
                    print(f"Error generating Key PDF for paper {i}: {e}")
        
        return jsonify({
            'status': 'success',
            'message': f'All questions configured! {num_papers} paper(s) generated successfully. PDFs created: {len(pdf_files)}',
            'redirect': url_for('teacher_dashboard'),
            'completed': True,
            'pdf_files': pdf_files,
            'pdf_urls': pdf_urls,
            'paper_folder': paper_folder.name
        })
    else:
        return jsonify({
            'status': 'success',
            'message': f'Question {current_question} saved',
            'redirect': url_for('configure_question'),
            'completed': False
        })

@app.route('/download_pdf/<folder>/<filename>')
@teacher_required
def download_pdf(folder, filename):
    """Download a generated PDF file"""
    try:
        file_path = Path('Generated Papers') / folder / filename
        
        if not file_path.exists():
            flash('PDF file not found', 'error')
            return redirect(url_for('teacher_dashboard'))
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'Error downloading PDF: {str(e)}', 'error')
        return redirect(url_for('teacher_dashboard'))

@app.route('/view_generated_papers')
@teacher_required
def view_generated_papers():
    """View all generated paper sets"""
    try:
        papers_folder = Path('Generated Papers')
        paper_sets = []
        
        if papers_folder.exists():
            for folder in sorted(papers_folder.iterdir(), reverse=True):
                if folder.is_dir():
                    md_files = list(folder.glob('*.md'))
                    pdf_files = list(folder.glob('*.pdf'))
                    
                    paper_sets.append({
                        'folder_name': folder.name,
                        'created': datetime.fromtimestamp(folder.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'num_papers': len(md_files),
                        'has_pdfs': len(pdf_files) > 0,
                        'pdf_files': [f.name for f in pdf_files]
                    })
        
        return render_template('view_papers.html', paper_sets=paper_sets)
    
    except Exception as e:
        flash(f'Error loading papers: {str(e)}', 'error')
        return redirect(url_for('teacher_dashboard'))

def convert_latex_to_mathml(text):
    """Pre-process LaTeX math expressions ($...$, $$...$$) into MathML for PDF rendering"""
    def replace_display_math(match):
        latex = match.group(1).strip()
        try:
            mathml = latex2mathml.converter.convert(latex)
            return f'<div style="text-align:center;margin:10px 0;">{mathml}</div>'
        except Exception:
            return match.group(0)  # Return original if conversion fails
    
    def replace_inline_math(match):
        latex = match.group(1).strip()
        try:
            return latex2mathml.converter.convert(latex)
        except Exception:
            return match.group(0)  # Return original if conversion fails

    # Handle display math first: $$...$$
    text = re.sub(r'\$\$(.*?)\$\$', replace_display_math, text, flags=re.DOTALL)
    # Handle inline math: $...$
    text = re.sub(r'(?<!\$)\$([^\$]+?)\$(?!\$)', replace_inline_math, text)
    return text

def convert_md_to_pdf(md_file_path: str, pdf_file_path: str):
    """Convert markdown file to PDF using weasyprint with LaTeX math support"""
    # Read markdown file
    with open(md_file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Pre-process LaTeX math expressions into MathML
    md_content = convert_latex_to_mathml(md_content)
    
    # Convert markdown to HTML
    html_content = markdown.markdown(md_content, extensions=['extra', 'codehilite'])
    
    # Add CSS styling
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 100%;
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                margin-top: 0;
            }}
            h2 {{
                color: #34495e;
                border-bottom: 2px solid #95a5a6;
                padding-bottom: 8px;
                margin-top: 30px;
            }}
            h3 {{
                color: #7f8c8d;
                margin-top: 20px;
            }}
            p {{
                margin: 10px 0;
            }}
            strong {{
                color: #2c3e50;
            }}
            hr {{
                border: none;
                border-top: 1px solid #bdc3c7;
                margin: 20px 0;
            }}
            code {{
                background-color: #f8f9fa;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }}
            pre {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #3498db;
                overflow-x: auto;
            }}
            ul, ol {{
                margin: 10px 0;
                padding-left: 30px;
            }}
            li {{
                margin: 5px 0;
            }}
            /* Math styling */
            math {{
                font-family: 'Times New Roman', 'STIX Two Math', serif;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Convert HTML to PDF
    HTML(string=styled_html).write_pdf(pdf_file_path)

@app.route('/submit', methods=['POST'])
@teacher_required
def submit_question():
    try:
        # Get form data
        title = request.form.get('title')
        full_question_text = request.form.get('full_question_text')
        question_type = request.form.get('question_type')
        subject = request.form.get('subject')
        topic = request.form.get('topic')
        subtopic = request.form.get('subtopic')
        difficulty_level = request.form.get('difficulty_level')
        estimated_time = request.form.get('estimated_time')
        bloom_level = request.form.get('bloom_level')
        generate_ai_questions = request.form.get('generate_ai_questions') == 'on'
        ai_notes = request.form.get('ai_notes', '')
        
        # Get explanation if provided
        add_explanation = request.form.get('add_explanation') == 'on'
        explanation_text = request.form.get('explanation_text', '')
        
        # Get teacher ID from session
        teacher_id = session.get('user_id')

        # Validate required fields
        if not all([title, full_question_text, question_type, subject, topic,
                   difficulty_level, estimated_time, bloom_level]):
            return jsonify({
                'status': 'error',
                'message': 'All required fields must be filled'
            }), 400

        # Insert original question into database with teacher_id and has_explanation
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO questions (title, question_type, subject, topic, subtopic, difficulty_level, estimated_time, bloom_level,
                                 is_ai_generated, ai_generation_notes, teacher_id, has_explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, question_type, subject, topic, subtopic,
              difficulty_level, int(estimated_time), bloom_level, False, None, teacher_id, add_explanation and bool(explanation_text.strip())))

        question_id = cursor.lastrowid

        # Create folder structures
        folder_path = create_folder_structure(subject, topic, subtopic)

        # Save markdown file
        file_path = save_markdown_file(folder_path, question_id, full_question_text)
        
        # Save explanation if provided
        if add_explanation and explanation_text.strip():
            explanation_file_path = folder_path / f"{question_id}_explanation.md"
            with open(explanation_file_path, 'w', encoding='utf-8') as f:
                f.write(explanation_text)

        generated_questions = []


        # Generate AI questions if requested
        if generate_ai_questions:
            try:
                # Use Groq API with default key
                generator = QuestionGenerator()

                # Generate 3 AI questions based on the original
                ai_questions = generator.generate_multiple_questions(
                    question_markdown=full_question_text,
                    difficulty=difficulty_level,
                    bloom_level=bloom_level,
                    count=3,
                    additional_notes=ai_notes
                )

                # Get original answer if it exists (to pass to AI for variant answer generation)
                original_answer = request.form.get('correct_answer')
                original_rubric = request.form.get('answer_rubric')

                # Save each AI-generated question
                for i, ai_question in enumerate(ai_questions):
                    ai_title = f"{title} - AI Variant {i+1}"

                    cursor.execute('''
                        INSERT INTO questions (title, question_type, subject, topic, subtopic,
                                             difficulty_level, estimated_time, bloom_level,
                                             is_ai_generated, ai_generation_notes, parent_question_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (ai_title, question_type, subject, topic, subtopic,
                          difficulty_level, int(estimated_time), bloom_level, True, ai_notes, question_id))

                    ai_question_id = cursor.lastrowid
                    ai_file_path = save_markdown_file(folder_path, ai_question_id, ai_question)

                    # Generate answer for this AI variant if original has an answer
                    if original_answer or original_rubric:
                        try:
                            variant_response_str = generator.generate_answer_for_variant(
                                original_question=full_question_text,
                                original_answer=original_answer,
                                original_rubric=original_rubric,
                                ai_generated_question=ai_question,
                                question_type=question_type
                            )
                            
                            variant_answer = ""
                            variant_rubric = ""
                            
                            if variant_response_str and not variant_response_str.startswith("Error"):
                                try:
                                    import json
                                    cleaned_response = variant_response_str.strip()
                                    if cleaned_response.startswith('```json'):
                                        cleaned_response = cleaned_response[7:]
                                    elif cleaned_response.startswith('```'):
                                        cleaned_response = cleaned_response[3:]
                                    if cleaned_response.endswith('```'):
                                        cleaned_response = cleaned_response[:-3]
                                    
                                    parsed = json.loads(cleaned_response)
                                    variant_answer = parsed.get("answer", "")
                                    variant_rubric = parsed.get("rubric", "")
                                except Exception as e:
                                    # Fallback if json parsing fails
                                    print(f"JSON Parsing failed: {e}. Falling back to strings.")
                                    variant_answer = variant_response_str
                                
                                try:
                                    max_marks_val = float(request.form.get('max_marks', 1.0))
                                except ValueError:
                                    max_marks_val = 1.0
                                    
                                cursor.execute('''
                                    INSERT INTO question_answers (question_id, correct_answer, rubric, max_marks)
                                    VALUES (?, ?, ?, ?)
                                ''', (ai_question_id, variant_answer, variant_rubric, max_marks_val))
                                
                        except Exception as ans_error:
                            print(f"Answer generation error for variant {i+1}: {ans_error}")

                    generated_questions.append({
                        'id': ai_question_id,
                        'title': ai_title,
                        'file_path': ai_file_path
                    })

            except Exception as ai_error:
                # Continue with original question even if AI generation fails
                print(f"AI generation error: {ai_error}")

        # Save correct answer or rubric if provided
        correct_answer = request.form.get('correct_answer')
        answer_rubric = request.form.get('answer_rubric')
        max_marks = request.form.get('max_marks')
        
        final_answer = correct_answer.strip() if correct_answer else ""
        final_rubric = answer_rubric.strip() if answer_rubric else ""
            
        if final_answer or final_rubric:
            try:
                max_marks_val = float(max_marks) if max_marks else 1.0
            except ValueError:
                max_marks_val = 1.0

            cursor.execute('''
                INSERT INTO question_answers (question_id, correct_answer, rubric, max_marks)
                VALUES (?, ?, ?, ?)
            ''', (question_id, final_answer, final_rubric, max_marks_val))

        conn.commit()
        conn.close()

        # Prepare response data
        question_data = {
            'id': question_id,
            'title': title,
            'question_type': question_type,
            'subject': subject,
            'topic': topic,
            'subtopic': subtopic,
            'difficulty_level': difficulty_level,
            'estimated_time': estimated_time,
            'bloom_level': bloom_level,
            'file_path': file_path,
            'ai_generated_count': len(generated_questions),
            'ai_questions': generated_questions,
            'created_at': datetime.now().isoformat()
        }

        message = f'Question submitted successfully! Saved as ID: {question_id}'
        if generated_questions:
            message += f' with {len(generated_questions)} AI-generated variants.'

        return jsonify({
            'status': 'success',
            'message': message,
            'data': question_data
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error submitting question: {str(e)}'
        }), 400

@app.route('/preview_markdown', methods=['POST'])
def preview_markdown():
    """API endpoint to preview markdown content"""
    try:
        markdown_text = request.json.get('markdown', '')
        # Here you could use a markdown library to convert to HTML
        # For now, we'll return the raw text (the frontend will handle conversion)
        return jsonify({
            'status': 'success',
            'markdown': markdown_text
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/questions')
@login_required
def view_questions():
    """View all questions in the database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, title, question_type, subject, topic, subtopic,
                   difficulty_level, estimated_time, bloom_level,
                   is_ai_generated, ai_generation_notes, parent_question_id, created_at
            FROM questions
            ORDER BY created_at DESC
        ''')

        questions = []
        for row in cursor.fetchall():
            questions.append({
                'id': row[0],
                'title': row[1],
                'question_type': row[2],
                'subject': row[3],
                'topic': row[4],
                'subtopic': row[5],
                'difficulty_level': row[6],
                'estimated_time': row[7],
                'bloom_level': row[8],
                'is_ai_generated': row[9],
                'ai_generation_notes': row[10],
                'parent_question_id': row[11],
                'created_at': row[12]
            })

        conn.close()

        return jsonify({
            'status': 'success',
            'questions': questions,
            'total': len(questions)
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/practice')
@student_required
def practice():
    """Student practice interface"""
    return render_template('practice.html')

@app.route('/api/practice/tree')
@student_required
def get_practice_tree():
    """Get hierarchical tree structure for practice"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT DISTINCT subject, topic, subtopic, COUNT(*) as question_count
            FROM questions
            GROUP BY subject, topic, subtopic
            ORDER BY subject, topic, subtopic
        ''')

        tree = {}
        for row in cursor.fetchall():
            subject, topic, subtopic, count = row

            if subject not in tree:
                tree[subject] = {}

            if topic not in tree[subject]:
                tree[subject][topic] = {}

            subtopic_key = subtopic if subtopic else "General"
            tree[subject][topic][subtopic_key] = count

        conn.close()

        return jsonify({
            'status': 'success',
            'tree': tree
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/practice/questions')
@student_required
def get_practice_questions():
    """Get questions for practice based on filters"""
    try:
        subject = request.args.get('subject')
        topic = request.args.get('topic')
        subtopic = request.args.get('subtopic')

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        query = '''
            SELECT id, title, question_type, difficulty_level, estimated_time, bloom_level
            FROM questions
            WHERE subject = ? AND topic = ?
        '''
        params = [subject, topic]

        if subtopic and subtopic != "General":
            query += ' AND subtopic = ?'
            params.append(subtopic)
        elif subtopic == "General":
            query += ' AND (subtopic IS NULL OR subtopic = "")'

        query += ' ORDER BY difficulty_level, title'

        cursor.execute(query, params)

        questions = []
        for row in cursor.fetchall():
            questions.append({
                'id': row[0],
                'title': row[1],
                'question_type': row[2],
                'difficulty_level': row[3],
                'estimated_time': row[4],
                'bloom_level': row[5]
            })

        conn.close()

        return jsonify({
            'status': 'success',
            'questions': questions
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/practice/question/<int:question_id>')
@student_required
def get_question_content(question_id):
    """Get full question content for practice"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT title, question_type, subject, topic, subtopic,
                   difficulty_level, estimated_time, bloom_level
            FROM questions
            WHERE id = ?
        ''', (question_id,))

        question_data = cursor.fetchone()
        if not question_data:
            return jsonify({
                'status': 'error',
                'message': 'Question not found'
            }), 404

        # Read markdown file
        subject, topic, subtopic = question_data[2], question_data[3], question_data[4]
        folder_path = create_folder_structure(subject, topic, subtopic)
        file_path = folder_path / f"{question_id}.md"

        content = ""
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

        conn.close()

        return jsonify({
            'status': 'success',
            'question': {
                'id': question_id,
                'title': question_data[0],
                'question_type': question_data[1],
                'subject': question_data[2],
                'topic': question_data[3],
                'subtopic': question_data[4],
                'difficulty_level': question_data[5],
                'estimated_time': question_data[6],
                'bloom_level': question_data[7],
                'content': content
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/paper/subjects')
@teacher_required
def get_paper_subjects():
    """Get available subjects for paper generation"""
    try:
        paper_gen = EnhancedPaperGeneration(DATABASE_PATH)
        subjects = paper_gen.get_available_subjects()

        return jsonify({
            'status': 'success',
            'subjects': subjects
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/paper/topics')
@teacher_required
def get_paper_topics():
    """Get available topics for a subject"""
    try:
        subject = request.args.get('subject')
        if not subject:
            return jsonify({
                'status': 'error',
                'message': 'Subject parameter is required'
            }), 400

        paper_gen = EnhancedPaperGeneration(DATABASE_PATH)
        topics = paper_gen.get_topics_for_subject(subject)

        return jsonify({
            'status': 'success',
            'topics': topics
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/paper/subtopics')
@teacher_required
def get_paper_subtopics():
    """Get available subtopics for a subject and topic"""
    try:
        subject = request.args.get('subject')
        topic = request.args.get('topic')

        if not subject or not topic:
            return jsonify({
                'status': 'error',
                'message': 'Subject and topic parameters are required'
            }), 400

        paper_gen = EnhancedPaperGeneration(DATABASE_PATH)
        subtopics = paper_gen.get_subtopics_for_topic(subject, topic)

        return jsonify({
            'status': 'success',
            'subtopics': subtopics
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/paper/generate', methods=['POST'])
@teacher_required
def generate_paper():
    """Generate a question paper based on criteria"""
    try:
        criteria = request.json

        # Validate required fields
        if not criteria.get('total_questions'):
            return jsonify({
                'status': 'error',
                'message': 'Total questions is required'
            }), 400

        paper_gen = EnhancedPaperGeneration(DATABASE_PATH)
        result = paper_gen.generate_paper(criteria)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error generating paper: {str(e)}'
        }), 400

@app.route('/api/paper/save', methods=['POST'])
@teacher_required
def save_paper():
    """Save generated paper to file"""
    try:
        data = request.json
        paper_data = data.get('paper_data')
        filename = data.get('filename', f'paper_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        format_type = data.get('format', 'markdown')

        if not paper_data:
            return jsonify({
                'status': 'error',
                'message': 'Paper data is required'
            }), 400

        paper_gen = EnhancedPaperGeneration(DATABASE_PATH)
        file_path = paper_gen.save_paper_to_file(paper_data, filename, format_type)

        return jsonify({
            'status': 'success',
            'message': 'Paper saved successfully',
            'file_path': file_path
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error saving paper: {str(e)}'
        }), 400

# ==================== AUTO-GENERATE PAPER ENDPOINTS ====================

@app.route('/api/paper/auto/topics')
@teacher_required
def auto_paper_topics():
    """Get all available topics grouped by subject for paper auto-generation"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT subject, topic, COUNT(*) as question_count
            FROM questions
            WHERE is_ai_generated = 0 OR acceptance_status = 'accepted'
            GROUP BY subject, topic
            ORDER BY subject, topic
        ''')

        topics = []
        for row in cursor.fetchall():
            topics.append({
                'subject': row[0],
                'topic': row[1],
                'question_count': row[2]
            })

        conn.close()
        return jsonify({'status': 'success', 'topics': topics})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/paper/auto/check')
@teacher_required
def auto_paper_check():
    """Check available question families per type for given topics"""
    try:
        selected_topics = request.args.getlist('topics')

        if not selected_topics:
            return jsonify({'status': 'error', 'message': 'No topics selected'}), 400

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Build topic filter
        topic_conditions = []
        params = []
        for topic in selected_topics:
            if ':' in topic:
                subject, topic_name = topic.split(':', 1)
                topic_conditions.append('(subject = ? AND topic = ?)')
                params.extend([subject, topic_name])

        if not topic_conditions:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Invalid topic format'}), 400

        topic_filter = ' OR '.join(topic_conditions)

        # Get all question type counts requested
        type_counts = {}
        for key, value in request.args.items():
            if key.startswith('type_'):
                qtype = key[5:]  # strip 'type_' prefix
                type_counts[qtype] = int(value)

        availability = {}
        for qtype, requested in type_counts.items():
            # Count unique question families for this type and topics
            # A "family" is: the parent question (parent_question_id IS NULL) grouped with its variants
            # For original questions: COALESCE(parent_question_id, id) gives the family root
            cursor.execute(f'''
                SELECT COUNT(DISTINCT COALESCE(parent_question_id, id)) as family_count
                FROM questions
                WHERE ({topic_filter})
                  AND question_type = ?
                  AND (is_ai_generated = 0 OR acceptance_status = 'accepted')
            ''', params + [qtype])

            result = cursor.fetchone()
            available_families = result[0] if result else 0

            availability[qtype] = {
                'requested': requested,
                'available_families': available_families
            }

        conn.close()
        return jsonify({'status': 'success', 'availability': availability})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/paper/auto/generate', methods=['POST'])
@teacher_required
def auto_paper_generate():
    """Auto-generate papers by randomly picking questions without replacement.
    
    Once a question is picked, its entire family (parent + all variants) is excluded
    from further selection. Each paper variant gets its own independent random selection.
    """
    import random

    try:
        data = request.json
        selected_topics = data.get('topics', [])
        type_counts = data.get('question_type_counts', {})
        num_papers = int(data.get('num_papers', 1))

        if not selected_topics:
            return jsonify({'status': 'error', 'message': 'No topics selected'}), 400
        if not type_counts:
            return jsonify({'status': 'error', 'message': 'No question types specified'}), 400

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Build topic filter
        topic_conditions = []
        topic_params = []
        for topic in selected_topics:
            if ':' in topic:
                subject, topic_name = topic.split(':', 1)
                topic_conditions.append('(subject = ? AND topic = ?)')
                topic_params.extend([subject, topic_name])

        if not topic_conditions:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Invalid topic format'}), 400

        topic_filter = ' OR '.join(topic_conditions)

        # For each question type, get all eligible questions grouped by family
        # family_id = COALESCE(parent_question_id, id)
        question_pool = {}  # { question_type: { family_id: [question_rows] } }

        for qtype in type_counts:
            cursor.execute(f'''
                SELECT id, title, question_type, subject, topic, subtopic,
                       difficulty_level, estimated_time, bloom_level,
                       COALESCE(parent_question_id, id) as family_id
                FROM questions
                WHERE ({topic_filter})
                  AND question_type = ?
                  AND (is_ai_generated = 0 OR acceptance_status = 'accepted')
                ORDER BY family_id
            ''', topic_params + [qtype])

            families = {}
            for row in cursor.fetchall():
                fam_id = row[9]
                if fam_id not in families:
                    families[fam_id] = []
                families[fam_id].append({
                    'id': row[0],
                    'title': row[1],
                    'question_type': row[2],
                    'subject': row[3],
                    'topic': row[4],
                    'subtopic': row[5],
                    'difficulty_level': row[6],
                    'estimated_time': row[7],
                    'bloom_level': row[8],
                    'family_id': fam_id
                })

            question_pool[qtype] = families

        # Validate we have enough families for each type
        for qtype, count in type_counts.items():
            available = len(question_pool.get(qtype, {}))
            if available < count:
                conn.close()
                return jsonify({
                    'status': 'error',
                    'message': f'Not enough {qtype} questions. Need {count}, but only {available} unique question families available.'
                }), 400

        # Create folder for papers
        folder_name = f"paper_set_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        paper_folder = Path('Generated Papers') / folder_name
        paper_folder.mkdir(parents=True, exist_ok=True)

        total_questions = sum(type_counts.values())
        pdf_urls = []
        md_urls = []

        for paper_idx in range(1, num_papers + 1):
            paper_questions = []

            # For each question type, randomly pick families without replacement
            for qtype, count in type_counts.items():
                families = question_pool.get(qtype, {})
                family_ids = list(families.keys())
                random.shuffle(family_ids)

                picked_families = family_ids[:count]

                for fam_id in picked_families:
                    # From the family, randomly pick one member
                    members = families[fam_id]
                    chosen = random.choice(members)
                    paper_questions.append(chosen)

            # Shuffle the final order so types are mixed
            random.shuffle(paper_questions)

            # Build paper markdown
            md_content = f"# Paper {paper_idx}\n\n"
            md_key_content = f"# Paper {paper_idx} - Answer Key\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for q_num, q in enumerate(paper_questions, 1):
                # Read the question markdown file
                subject = q['subject']
                topic = q['topic']
                subtopic = q['subtopic']
                q_id = q['id']

                folder_path = create_folder_structure(subject, topic, subtopic)
                file_path = folder_path / f"{q_id}.md"

                question_content = ""
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        question_content = f.read()
                else:
                    # Try without subtopic
                    folder_path_alt = create_folder_structure(subject, topic, None)
                    file_path_alt = folder_path_alt / f"{q_id}.md"
                    if file_path_alt.exists():
                        with open(file_path_alt, 'r', encoding='utf-8') as f:
                            question_content = f.read()
                    else:
                        # Search all locations
                        base_path = Path(QUESTION_BANK_FOLDER)
                        for md_file in base_path.rglob(f"{q_id}.md"):
                            with open(md_file, 'r', encoding='utf-8') as f:
                                question_content = f.read()
                            break

                if not question_content:
                    question_content = f"[Question content not found for ID: {q_id}]"

                md_content += f"## Question {q_num}\n\n{question_content}\n\n---\n\n"
                
                # Fetch answers for the key
                cursor = conn.cursor()
                cursor.execute("SELECT correct_answer, rubric FROM question_answers WHERE question_id = ?", (q_id,))
                ans_rec = cursor.fetchone()
                correct_ans = ans_rec[0] if ans_rec and ans_rec[0] else ""
                rubric = ans_rec[1] if ans_rec and ans_rec[1] else ""
                
                md_key_content += f"## Question {q_num}\n\n{question_content}\n"
                if correct_ans:
                    md_key_content += f"\n**Formal Answer:**\n{correct_ans}\n"
                if rubric:
                    md_key_content += f"\n**Grading Rubric:**\n{rubric}\n"
                md_key_content += "\n---\n\n"

            # Write MD files
            md_file_path = paper_folder / f"paper_{paper_idx}.md"
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
                
            md_key_file_path = paper_folder / f"paper_{paper_idx}_key.md"
            with open(md_key_file_path, 'w', encoding='utf-8') as f:
                f.write(md_key_content)

            md_urls.append({
                'name': f"paper_{paper_idx}.md",
                'url': url_for('download_pdf', folder=paper_folder.name, filename=f"paper_{paper_idx}.md")
            })

            # Generate PDFs
            pdf_file_path = paper_folder / f"paper_{paper_idx}.pdf"
            key_pdf_file_path = paper_folder / f"paper_{paper_idx}_key.pdf"
            
            try:
                convert_md_to_pdf(str(md_file_path), str(pdf_file_path))
                pdf_urls.append({
                    'name': f"paper_{paper_idx}.pdf",
                    'url': url_for('download_pdf', folder=paper_folder.name, filename=f"paper_{paper_idx}.pdf")
                })
                print(f"[AUTO-PAPER] Generated PDF: {pdf_file_path}")
            except Exception as pdf_err:
                print(f"[AUTO-PAPER] PDF generation failed for paper {paper_idx}: {pdf_err}")
                
            try:
                convert_md_to_pdf(str(md_key_file_path), str(key_pdf_file_path))
                pdf_urls.append({
                    'name': f"paper_{paper_idx}_key.pdf",
                    'url': url_for('download_pdf', folder=paper_folder.name, filename=f"paper_{paper_idx}_key.pdf")
                })
                print(f"[AUTO-PAPER] Generated Answer Key PDF: {key_pdf_file_path}")
            except Exception as pdf_err:
                print(f"[AUTO-PAPER] Answer Key PDF generation failed for paper {paper_idx}: {pdf_err}")
                print(f"[AUTO-PAPER] PDF generation failed for paper {paper_idx}: {pdf_err}")

        conn.close()

        return jsonify({
            'status': 'success',
            'message': f'Generated {num_papers} paper(s) with {total_questions} questions each',
            'num_papers': num_papers,
            'total_questions': total_questions,
            'pdf_urls': pdf_urls,
            'md_urls': md_urls,
            'paper_folder': paper_folder.name
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Error generating papers: {str(e)}'
        }), 400


@app.route('/random-practice')
@student_required
def random_practice():
    """Random question practice interface"""
    return render_template('random_practice.html')

@app.route('/api/practice/topics')
@student_required
def get_practice_topics():
    """Get all available topics for practice selection"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT DISTINCT subject, topic, COUNT(*) as question_count
            FROM questions
            GROUP BY subject, topic
            ORDER BY subject, topic
        ''')

        topics = []
        for row in cursor.fetchall():
            topics.append({
                'subject': row[0],
                'topic': row[1],
                'question_count': row[2]
            })

        conn.close()

        return jsonify({
            'status': 'success',
            'topics': topics
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/practice/random-question')
@student_required
def get_random_question():
    """Get a random question based on selected topics"""
    try:
        selected_topics = request.args.getlist('topics')  # List of "subject:topic" strings

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        if selected_topics and selected_topics != ['all']:
            # Build query for specific topics
            topic_conditions = []
            params = []

            for topic in selected_topics:
                if ':' in topic:
                    subject, topic_name = topic.split(':', 1)
                    topic_conditions.append('(subject = ? AND topic = ?)')
                    params.extend([subject, topic_name])

            if topic_conditions:
                query = f'''
                    SELECT id, title, question_type, subject, topic, subtopic,
                           difficulty_level, estimated_time, bloom_level
                    FROM questions
                    WHERE {' OR '.join(topic_conditions)}
                    ORDER BY RANDOM()
                    LIMIT 1
                '''
            else:
                # Fallback to all questions if no valid topics
                query = '''
                    SELECT id, title, question_type, subject, topic, subtopic,
                           difficulty_level, estimated_time, bloom_level
                    FROM questions
                    ORDER BY RANDOM()
                    LIMIT 1
                '''
                params = []
        else:
            # Get random question from all topics
            query = '''
                SELECT id, title, question_type, subject, topic, subtopic,
                       difficulty_level, estimated_time, bloom_level
                FROM questions
                ORDER BY RANDOM()
                LIMIT 1
            '''
            params = []

        cursor.execute(query, params)
        question_data = cursor.fetchone()

        if not question_data:
            return jsonify({
                'status': 'error',
                'message': 'No questions found for the selected topics'
            }), 404

        # Read markdown file
        question_id = question_data[0]
        subject, topic, subtopic = question_data[3], question_data[4], question_data[5]
        folder_path = create_folder_structure(subject, topic, subtopic)
        file_path = folder_path / f"{question_id}.md"

        content = ""
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

        conn.close()

        return jsonify({
            'status': 'success',
            'question': {
                'id': question_id,
                'title': question_data[1],
                'question_type': question_data[2],
                'subject': question_data[3],
                'topic': question_data[4],
                'subtopic': question_data[5],
                'difficulty_level': question_data[6],
                'estimated_time': question_data[7],
                'bloom_level': question_data[8],
                'content': content
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

# ==================== TEACHER BACKEND API ENDPOINTS ====================

@app.route('/api/teacher/questions', methods=['GET'])
@teacher_required
def teacher_get_questions():
    """Get all questions for teacher management"""
    try:
        backend = TeacherBackend(DATABASE_PATH, QUESTION_BANK_FOLDER)

        # Get filters from query parameters
        filters = {}
        if request.args.get('subject'):
            filters['subject'] = request.args.get('subject')
        if request.args.get('topic'):
            filters['topic'] = request.args.get('topic')
        if request.args.get('difficulty_level'):
            filters['difficulty_level'] = request.args.get('difficulty_level')
        if request.args.get('question_type'):
            filters['question_type'] = request.args.get('question_type')

        result = backend.get_all_questions(filters if filters else None)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/teacher/question/<int:question_id>', methods=['GET'])
@teacher_required
def teacher_get_question(question_id):
    """Get a specific question for editing"""
    try:
        backend = TeacherBackend(DATABASE_PATH, QUESTION_BANK_FOLDER)
        result = backend.get_question(question_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/teacher/question', methods=['POST'])
@teacher_required
def teacher_add_question():
    """Add a new question via API"""
    try:
        data = request.get_json()
        backend = TeacherBackend(DATABASE_PATH, QUESTION_BANK_FOLDER)
        result = backend.add_question(data)
        status_code = 200 if result['status'] == 'success' else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/teacher/question/<int:question_id>', methods=['PUT'])
@teacher_required
def teacher_update_question(question_id):
    """Update an existing question"""
    try:
        data = request.get_json()
        backend = TeacherBackend(DATABASE_PATH, QUESTION_BANK_FOLDER)
        result = backend.update_question(question_id, data)
        status_code = 200 if result['status'] == 'success' else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/teacher/question/<int:question_id>', methods=['DELETE'])
@teacher_required
def teacher_delete_question(question_id):
    """Delete a question"""
    try:
        backend = TeacherBackend(DATABASE_PATH, QUESTION_BANK_FOLDER)
        result = backend.delete_question(question_id)
        status_code = 200 if result['status'] == 'success' else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/teacher/paper/generate', methods=['POST'])
@teacher_required
def teacher_generate_paper():
    """Generate a question paper using enhanced generation"""
    try:
        criteria = request.get_json()
        paper_gen = EnhancedPaperGeneration(DATABASE_PATH)
        result = paper_gen.generate_paper(criteria)
        status_code = 200 if result['status'] in ['success', 'warning'] else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/teacher/paper/save', methods=['POST'])
@teacher_required
def teacher_save_paper():
    """Save generated paper to file"""
    try:
        data = request.get_json()
        paper_gen = EnhancedPaperGeneration(DATABASE_PATH)
        result = paper_gen.save_paper(
            data.get('paper_data'),
            data.get('filename', f'paper_{datetime.now().strftime("%Y%m%d_%H%M%S")}'),
            data.get('format', 'markdown')
        )
        status_code = 200 if result['status'] == 'success' else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/teacher/statistics', methods=['GET'])
@teacher_required
def teacher_get_statistics():
    """Get statistics about questions in the database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Total questions
        cursor.execute('SELECT COUNT(*) FROM questions')
        total_questions = cursor.fetchone()[0]

        # Questions by subject
        cursor.execute('SELECT subject, COUNT(*) FROM questions GROUP BY subject')
        by_subject = {row[0]: row[1] for row in cursor.fetchall()}

        # Questions by difficulty
        cursor.execute('SELECT difficulty_level, COUNT(*) FROM questions GROUP BY difficulty_level')
        by_difficulty = {row[0]: row[1] for row in cursor.fetchall()}

        # Questions by type
        cursor.execute('SELECT question_type, COUNT(*) FROM questions GROUP BY question_type')
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        # AI generated count
        cursor.execute('SELECT COUNT(*) FROM questions WHERE is_ai_generated = 1')
        ai_generated = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            'status': 'success',
            'statistics': {
                'total_questions': total_questions,
                'by_subject': by_subject,
                'by_difficulty': by_difficulty,
                'by_type': by_type,
                'ai_generated': ai_generated
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/generate', methods=['POST'])
def generate():
    prompt = request.json.get('prompt')
    
    completion = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt  # Your existing prompt variable
            }
        ],
        temperature=1,
        max_completion_tokens=8192,
        top_p=1,
        reasoning_effort="medium",
        stream=True,
        stop=None
    )
    
    def generate_stream():
        for chunk in completion:
            content = chunk.choices[0].delta.content or ""
            yield content
    
    return Response(generate_stream(), mimetype='text/plain')

@app.route('/api/questions/all', methods=['GET'])
@teacher_required
def get_all_questions():
    """Get all questions with basic information"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, title, question_type, subject, topic, subtopic,
                   difficulty_level, estimated_time, bloom_level
            FROM questions
            ORDER BY created_at DESC
        ''')

        questions = []
        for row in cursor.fetchall():
            questions.append({
                'id': row[0],
                'title': row[1],
                'question_type': row[2],
                'subject': row[3],
                'topic': row[4],
                'subtopic': row[5],
                'difficulty_level': row[6],
                'estimated_time': row[7],
                'bloom_level': row[8]
            })

        conn.close()

        return jsonify({
            'status': 'success',
            'questions': questions,
            'total': len(questions)
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/questions/filter', methods=['GET'])
@teacher_required
def filter_questions():
    """Filter questions based on criteria and acceptance status"""
    try:
        subject = request.args.get('subject')
        topic = request.args.get('topic')
        subtopic = request.args.get('subtopic')
        difficulty = request.args.get('difficulty')
        bloom_level = request.args.get('bloom_level')
        question_type = request.args.get('question_type')
        
        # Validate required fields
        required_fields = []
        if not subject:
            required_fields.append('subject')
        if not topic:
            required_fields.append('topic')
        if not difficulty:
            required_fields.append('difficulty')
        
        if required_fields:
            return jsonify({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(required_fields)}'
            }), 400

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Build query with acceptance status filter for AI questions
        query = '''
            SELECT id, title, question_type, subject, topic, subtopic,
                   difficulty_level, estimated_time, bloom_level
            FROM questions
            WHERE subject = ? 
              AND topic = ? 
              AND difficulty_level = ?
              AND (is_ai_generated = 0 OR acceptance_status = 'accepted')
        '''
        params = [subject, topic, difficulty]

        # Add optional filters
        if subtopic:
            query += ' AND subtopic = ?'
            params.append(subtopic)
        
        if bloom_level:
            query += ' AND bloom_level = ?'
            params.append(bloom_level)
        
        if question_type:
            query += ' AND question_type = ?'
            params.append(question_type)

        query += ' ORDER BY created_at DESC'

        cursor.execute(query, params)
        questions = []
        for row in cursor.fetchall():
            questions.append({
                'id': row[0],
                'title': row[1],
                'question_type': row[2],
                'subject': row[3],
                'topic': row[4],
                'subtopic': row[5],
                'difficulty_level': row[6],
                'estimated_time': row[7],
                'bloom_level': row[8]
            })
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'questions': questions,
            'total': len(questions)
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

# ============================================================================
# AI QUESTION VALIDATION ROUTES
# ============================================================================

@app.route('/api/check_feedback_needed/<int:question_id>', methods=['GET'])
@login_required
def check_feedback_needed(question_id):
    """Check if a question needs student feedback"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT is_ai_generated, acceptance_status 
            FROM questions 
            WHERE id = ?
        ''', (question_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'needs_feedback': False, 'reason': 'Question not found'})
        
        is_ai_generated, acceptance_status = result
        
        # Only AI-generated questions with 'pending' status need feedback
        needs_feedback = bool(is_ai_generated) and acceptance_status == 'pending'
        
        return jsonify({
            'needs_feedback': needs_feedback,
            'acceptance_status': acceptance_status,
            'is_ai_generated': bool(is_ai_generated)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit_feedback', methods=['POST'])
@login_required
@student_required
def submit_feedback():
    """Submit student feedback for an AI-generated question"""
    try:
        data = request.json
        question_id = data.get('question_id')
        student_id = session.get('user_id')
        
        # Required feedback fields
        is_question_clear = data.get('is_question_clear')
        is_answer_correct = data.get('is_answer_correct')
        is_difficulty_appropriate = data.get('is_difficulty_appropriate')
        additional_comments = data.get('additional_comments', '')
        
        # Calculate overall approval (all three must be True)
        overall_approval = all([
            is_question_clear,
            is_answer_correct,
            is_difficulty_appropriate
        ])
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if student already submitted feedback for this question
        cursor.execute('''
            SELECT id FROM question_feedback 
            WHERE question_id = ? AND student_id = ?
        ''', (question_id, student_id))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Feedback already submitted for this question'}), 400
        
        # Insert feedback
        cursor.execute('''
            INSERT INTO question_feedback (
                question_id, student_id, is_question_clear, 
                is_answer_correct, is_difficulty_appropriate, 
                overall_approval, additional_comments
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (question_id, student_id, is_question_clear, is_answer_correct,
              is_difficulty_appropriate, overall_approval, additional_comments))
        
        # Check approval ratio
        cursor.execute('''
            SELECT 
                COUNT(*) as total_feedback,
                SUM(CASE WHEN overall_approval = 1 THEN 1 ELSE 0 END) as approvals
            FROM question_feedback
            WHERE question_id = ?
        ''', (question_id,))
        
        total_feedback, approvals = cursor.fetchone()
        approvals = approvals or 0
        
        # Auto-accept if 9 out of last 10 approvals
        if total_feedback >= 10:
            # Get last 10 feedbacks
            cursor.execute('''
                SELECT overall_approval FROM question_feedback
                WHERE question_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            ''', (question_id,))
            
            last_10 = cursor.fetchall()
            last_10_approvals = sum(1 for (approval,) in last_10 if approval)
            
            if last_10_approvals >= 9:
                cursor.execute('''
                    UPDATE questions 
                    SET acceptance_status = 'accepted',
                        review_timestamp = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (question_id,))
                
                conn.commit()
                conn.close()
                
                return jsonify({
                    'success': True,
                    'message': 'Feedback submitted. Question auto-accepted!',
                    'approval_ratio': f'{last_10_approvals}/10',
                    'auto_accepted': True
                })
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Feedback submitted successfully',
            'approval_ratio': f'{approvals}/{total_feedback}',
            'auto_accepted': False
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/educator/review_ai_questions', methods=['GET'])
@login_required
@teacher_required
def review_ai_questions():
    """Get list of AI-generated questions for educator review"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                q.id, q.title, q.question_type, q.subject, q.topic,
                q.acceptance_status, q.educator_reviewed, q.reviewed_by,
                q.parent_question_id, q.created_at,
                COUNT(f.id) as feedback_count,
                SUM(CASE WHEN f.overall_approval = 1 THEN 1 ELSE 0 END) as approvals
            FROM questions q
            LEFT JOIN question_feedback f ON q.id = f.question_id
            WHERE q.is_ai_generated = 1
            GROUP BY q.id
            ORDER BY q.created_at DESC
        ''')
        
        questions = []
        for row in cursor.fetchall():
            approvals = row[11] or 0
            questions.append({
                'id': row[0],
                'title': row[1],
                'question_type': row[2],
                'subject': row[3],
                'topic': row[4],
                'acceptance_status': row[5],
                'educator_reviewed': bool(row[6]),
                'reviewed_by': row[7],
                'parent_question_id': row[8],
                'created_at': row[9],
                'feedback_count': row[10],
                'approvals': approvals,
                'approval_ratio': f'{approvals}/{row[10]}' if row[10] > 0 else 'No feedback'
            })
        
        conn.close()
        return jsonify({'questions': questions})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/educator/accept_question/<int:question_id>', methods=['POST'])
@login_required
@teacher_required
def educator_accept_question(question_id):
    """Educator manually accepts an AI-generated question"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE questions 
            SET acceptance_status = 'accepted',
                educator_reviewed = 1,
                reviewed_by = ?,
                review_timestamp = CURRENT_TIMESTAMP
            WHERE id = ? AND is_ai_generated = 1
        ''', (session.get('user_id'), question_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Question not found or not an AI-generated question'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Question accepted successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/educator/reject_question/<int:question_id>', methods=['POST'])
@login_required
@teacher_required
def educator_reject_question(question_id):
    """Educator rejects an AI-generated question (soft delete)"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE questions 
            SET acceptance_status = 'rejected',
                educator_reviewed = 1,
                reviewed_by = ?,
                review_timestamp = CURRENT_TIMESTAMP
            WHERE id = ? AND is_ai_generated = 1
        ''', (session.get('user_id'), question_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Question not found or not an AI-generated question'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Question rejected successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize database on startup
    init_database()
    app.run(host='0.0.0.0', port=5005)


from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, Response
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from functools import wraps
from ai import QuestionGenerator
from teacher_backend import TeacherBackend
from enhanced_paper_generation import EnhancedPaperGeneration
from groq import Groq

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'

# Database and folder configuration
DATABASE_PATH = 'question_bank.db'
QUESTION_BANK_FOLDER = 'Question Bank'

# Simple user credentials (in production, use proper database with hashed passwords)
USERS = {
    'teacher': {'password': 'teacher123', 'role': 'teacher'},
    'student': {'password': 'student123', 'role': 'student'},
}

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
    """Initialize the SQLite database with the required table"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Check if the table exists and get its schema
    cursor.execute("PRAGMA table_info(questions)")
    columns = [row[1] for row in cursor.fetchall()]

    if not columns:
        # Create new table with all columns
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_question_id) REFERENCES questions (id)
            )
        ''')
    else:
        # Add missing columns if they don't exist
        if 'is_ai_generated' not in columns:
            cursor.execute('ALTER TABLE questions ADD COLUMN is_ai_generated BOOLEAN DEFAULT FALSE')
        if 'ai_generation_notes' not in columns:
            cursor.execute('ALTER TABLE questions ADD COLUMN ai_generation_notes TEXT')
        if 'parent_question_id' not in columns:
            cursor.execute('ALTER TABLE questions ADD COLUMN parent_question_id INTEGER')

    conn.commit()
    conn.close()

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
    """Main landing page with login options"""
    return render_template('index.html')

@app.route('/teacher-login')
def teacher_login():
    """Teacher login page"""
    return render_template('teacher_login.html')

@app.route('/student-login')
def student_login():
    """Student login page"""
    return render_template('student_login.html')

@app.route('/login', methods=['POST'])
def login():
    """Handle login for both teachers and students"""
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')  # 'teacher' or 'student'

    if username in USERS and USERS[username]['password'] == password and USERS[username]['role'] == role:
        session['user_id'] = username
        session['role'] = role

        if role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    else:
        flash('Invalid credentials. Please try again.', 'error')
        if role == 'teacher':
            return redirect(url_for('teacher_login'))
        else:
            return redirect(url_for('student_login'))

@app.route('/logout')
def logout():
    """Logout user and clear session"""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

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

        # Validate required fields
        if not all([title, full_question_text, question_type, subject, topic,
                   difficulty_level, estimated_time, bloom_level]):
            return jsonify({
                'status': 'error',
                'message': 'All required fields must be filled'
            }), 400

        # Insert original question into database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO questions (title, question_type, subject, topic, subtopic,
                                 difficulty_level, estimated_time, bloom_level,
                                 is_ai_generated, ai_generation_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, question_type, subject, topic, subtopic,
              difficulty_level, int(estimated_time), bloom_level, False, None))

        question_id = cursor.lastrowid

        # Create folder structure
        folder_path = create_folder_structure(subject, topic, subtopic)

        # Save markdown file
        file_path = save_markdown_file(folder_path, question_id, full_question_text)

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

                    generated_questions.append({
                        'id': ai_question_id,
                        'title': ai_title,
                        'file_path': ai_file_path
                    })

            except Exception as ai_error:
                # Continue with original question even if AI generation fails
                print(f"AI generation error: {ai_error}")

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

@app.route('/create_paper')
@teacher_required
def create_paper():
    """Paper generation interface"""
    return render_template('create_paper.html',
                         question_types=QUESTION_TYPES,
                         bloom_levels=BLOOM_LEVELS,
                         difficulty_levels=DIFFICULTY_LEVELS)

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
                'id': question_data[0],
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

if __name__ == '__main__':
    # Initialize database on startup
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5005)

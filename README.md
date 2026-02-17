# 🎓 Question Paper Generation & Management System

A comprehensive web-based platform for creating, managing, and evaluating educational assessments with AI-powered question generation and automatic answer evaluation.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Application](#-running-the-application)
- [Usage Guide](#-usage-guide)
- [API Documentation](#-api-documentation)
- [Project Structure](#-project-structure)
- [Database Schema](#-database-schema)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### 🔐 Authentication & User Management
- **Dual Role System**: Separate teacher and student portals
- **Secure Authentication**: Password hashing with PBKDF2-SHA256
- **Session Management**: HTTP-only cookies with CSRF protection
- **Role-Based Access Control**: Protected routes for teachers and students

### 📝 Question Bank Management (Teacher Portal)
- **Multi-Type Support**: MCQ, True/False, Fill-in-the-Blank, Short Answer, Coding, Descriptive
- **Rich Text Editor**: Markdown support with LaTeX rendering (MathJax)
- **Hierarchical Organization**: Subject → Topic → Subtopic structure
- **Answer Key Storage**: Correct answers/rubrics for all question types
- **Explanation Support**: Optional detailed explanations for each question
- **Metadata Tracking**: Difficulty level, Bloom's taxonomy, estimated time, max marks

### 🤖 AI-Powered Question Generation
- **Variant Generation**: Create multiple variations of existing questions
- **Automatic Answer Generation**: AI generates corresponding answers for variants
- **Quality Control**: Teacher review and approval system for AI questions
- **Student Feedback Integration**: Collect and analyze student feedback
- **Acceptance Workflow**: Accept/reject AI-generated questions

### 📊 Student Practice & Evaluation
- **Interactive Practice Mode**: Browse questions by category
- **Instant Evaluation**: Automatic grading with Groq AI
- **Score Display**: Visual progress bars with color-coded feedback
- **Answer Reveal**: View correct answers after submission
- **Explanation Access**: Study detailed explanations
- **Performance Tracking**: Statistics for each question

### 📄 Paper Generation
- **Smart Selection**: Filter by subject, topic, difficulty, Bloom's level
- **Customizable Parameters**: Set total marks, time limits, number of questions
- **Multiple Formats**: Generate PDF and Markdown versions
- **Batch Generation**: Create multiple papers at once
- **Enhanced Generation**: Advanced algorithms for balanced papers

### 📈 Analytics & Metrics
- **Question Statistics**: Track attempts, average scores, min/max scores
- **Student Performance**: Individual submission history
- **Question Calibration**: Data-driven difficulty assessment

---

## 🛠️ Tech Stack

### Backend
- **Framework**: Flask 2.3.3 (Python web framework)
- **Database**: SQLite3 (Embedded relational database)
- **Authentication**: Werkzeug password hashing
- **AI Integration**: Groq API (GPT-OSS-20B model)
- **PDF Generation**: WeasyPrint + Cairo

### Frontend
- **CSS Framework**: Bootstrap 5.1.3
- **Icons**: Bootstrap Icons 1.7.2
- **Markdown Rendering**: marked.js
- **Math Rendering**: MathJax 3
- **JavaScript**: Vanilla JS (ES6+)

### Key Libraries
- `python-dotenv` - Environment variable management
- `markdown` - Server-side markdown processing
- `groq` - AI model integration
- `httpx` - Async HTTP client

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                  CLIENT SIDE                    │
├─────────────────────────────────────────────────┤
│  Browser (HTML/CSS/JS + Bootstrap + MathJax)    │
│  - Teacher Portal                               │
│  - Student Portal                               │
│  - Practice Interface                           │
└────────────────┬────────────────────────────────┘
                 │ HTTP/AJAX
┌────────────────▼────────────────────────────────┐
│                 SERVER SIDE                     │
├─────────────────────────────────────────────────┤
│  Flask Application (app.py)                     │
│  ├── Authentication (auth.py)                   │
│  ├── Question Generation (ai.py)                │
│  ├── Answer Evaluation (evaluator.py)           │
│  ├── Teacher Backend (teacher_backend.py)       │
│  └── Paper Generation (enhanced_paper_gen.py)   │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│              DATA LAYER                         │
├─────────────────────────────────────────────────┤
│  SQLite Database (question_bank.db)             │
│  ├── teachers, students                         │
│  ├── questions, question_answers                │
│  ├── question_feedback                          │
│  └── student_submissions                        │
│                                                  │
│  File System                                    │
│  ├── Question Bank/ (organized by hierarchy)    │
│  └── Generated Papers/ (PDF + MD outputs)       │
└─────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│           EXTERNAL SERVICES                     │
├─────────────────────────────────────────────────┤
│  Groq AI API (Question Gen + Evaluation)        │
└─────────────────────────────────────────────────┘
```

---

## 📦 Prerequisites

### Required
- **Python**: 3.8 or higher
- **pip**: Python package manager
- **Git**: Version control

### Optional but Recommended
- **Virtual Environment**: `venv` or `virtualenv`
- **Modern Browser**: Chrome, Firefox, Edge (latest versions)

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/question-paper-app.git
cd question-paper-app
```

### 2. Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies installed:**
- Flask 2.3.3
- WeasyPrint 59.0
- markdown 3.4.4
- groq 0.9.0
- python-dotenv 1.0.0
- And more (see `requirements.txt`)

### 4. Verify Installation

```bash
python -c "import flask, groq, markdown; print('All packages installed successfully!')"
```

---

## ⚙️ Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here-change-this-in-production
DATABASE_PATH=question_bank.db

# Groq AI Configuration
GROQ_API_KEY=your-groq-api-key-here

# Optional: Application Settings
FLASK_ENV=development
FLASK_DEBUG=1
```

**🔑 Getting a Groq API Key:**
1. Visit [https://console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy and paste into `.env` file

### 2. Directory Structure

The application automatically creates these directories:
- `Question Bank/` - Stores question markdown files
- `Generated Papers/` - Stores generated papers
- `question_bank.db` - SQLite database file

### 3. Database Initialization

The database is automatically initialized on first run with the following tables:
- `teachers` - Teacher accounts
- `students` - Student accounts
- `questions` - Question metadata
- `question_answers` - Answer keys and rubrics
- `question_feedback` - Student feedback on questions
- `student_submissions` - Answer submissions and scores

---

## 🎬 Running the Application

### Development Mode

```bash
# Activate virtual environment (if not already active)
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Run the application
python app.py
```

The application will start on `http://127.0.0.1:5000/`

### Production Mode

For production deployment, use a WSGI server like Gunicorn:

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

---

## 📖 Usage Guide

### First Time Setup

1. **Start the Application**
   ```bash
   python app.py
   ```

2. **Register as Teacher**
   - Navigate to `http://127.0.0.1:5000/`
   - Click "Register as Teacher"
   - Fill in registration form
   - Login with credentials

3. **Add Questions**
   - Go to "Manage Question Bank" tab
   - Click "Add New Question"
   - Fill in all fields (title, type, subject, topic, etc.)
   - Add correct answer/rubric
   - Optionally add explanation
   - Submit

### Teacher Workflow

#### Creating Questions
1. Navigate to Teacher Portal
2. Click **"Manage Question Bank"**
3. Fill in the question form:
   - Title (question text with Markdown/LaTeX)
   - Type (MCQ, True/False, etc.)
   - Subject, Topic, Subtopic
   - Difficulty, Bloom's Level, Time
   - Correct Answer/Rubric
   - Max Marks
   - Optional: Explanation
4. Submit question

#### Generating AI Variants
1. Browse to a question
2. Click **"Generate AI Variants"**
3. Select number of variants (1-5)
4. AI generates variations with answers
5. Review generated questions in **"Review AI Questions"** tab
6. Accept or reject with feedback

#### Creating Papers
1. Go to **"Generate Papers"** tab
2. Set filters:
   - Subject, Topic, Difficulty
   - Total marks, Time limit
   - Number of papers
3. Click **"Generate Papers"**
4. Download PDF/Markdown files from **"View Generated Papers"**

### Student Workflow

#### Practicing Questions
1. Register/Login as Student
2. Navigate to **"Practice"**
3. Browse by Subject → Topic → Subtopic
4. Select a question
5. Read and answer
6. Click **"Submit Answer"**
7. View score in modal
8. Click **"Show Answer"** to see correct answer
9. Click **"Show Explanation"** (if available)

#### Understanding Scores
- **Green (80-100%)**: Excellent! 🎉
- **Blue (60-79%)**: Good job! 👍
- **Yellow (40-59%)**: Room for improvement 💪
- **Red (0-39%)**: Keep practicing! 📚

---

## 🔌 API Documentation

### Authentication Endpoints

#### `POST /login`
Login as teacher or student

**Request Body:**
```json
{
  "username": "string",
  "password": "string",
  "role": "teacher" | "student"
}
```

#### `POST /register_student`
Register new student account

**Request Body:**
```json
{
  "username": "string",
  "password": "string",
  "confirm_password": "string",
  "full_name": "string",
  "email": "string (optional)"
}
```

### Question Management Endpoints

#### `POST /submit_question`
Submit new question (Teacher only)

**Form Data:**
- `title` - Question text
- `question_type` - MCQ, True/False, etc.
- `subject`, `topic`, `subtopic`
- `difficulty_level`, `bloom_level`, `estimated_time`
- `correct_answer` - Answer/rubric
- `max_marks`
- `explanation` (optional)

#### `GET /api/practice/categories`
Get hierarchical question categories

**Response:**
```json
{
  "categories": {
    "Mathematics": {
      "Algebra": ["Linear Equations", "Quadratics"],
      "Geometry": ["Triangles", "Circles"]
    }
  }
}
```

### Student Evaluation Endpoints

#### `POST /api/student/submit_answer`
Submit and evaluate student answer

**Request Body:**
```json
{
  "question_id": 123,
  "student_answer": "string"
}
```

**Response:**
```json
{
  "status": "success",
  "score": 4.5,
  "max_marks": 5.0,
  "percentage": 90.0,
  "correct_answer": "string",
  "question_type": "MCQ"
}
```

#### `GET /api/student/get_explanation/<question_id>`
Get explanation for a question

**Response:**
```json
{
  "status": "success",
  "has_explanation": true,
  "explanation": "Markdown text..."
}
```

### AI Generation Endpoints

#### `POST /api/generate_ai_questions`
Generate AI variants of a question

**Request Body:**
```json
{
  "question_id": 123,
  "num_variants": 3
}
```

#### `GET /api/educator/review_ai_questions`
Get pending AI questions for review

#### `POST /api/educator/accept_question/<question_id>`
Accept an AI-generated question

#### `POST /api/educator/reject_question/<question_id>`
Reject an AI-generated question

**Request Body:**
```json
{
  "reason": "string"
}
```

---

## 📁 Project Structure

```
Question_Paper_App/
├── app.py                          # Main Flask application
├── auth.py                         # Authentication module
├── ai.py                          # AI question generation
├── evaluator.py                   # Answer evaluation engine
├── teacher_backend.py             # Teacher-specific logic
├── enhanced_paper_generation.py   # Paper generation algorithms
├── requirements.txt               # Python dependencies
├── .env                           # Environment variables (create this)
├── .gitignore                     # Git ignore rules
├── question_bank.db               # SQLite database (auto-created)
│
├── static/                        # Static assets
│   ├── css/
│   │   └── style.css             # Custom styles
│   └── js/
│       ├── teacher.js            # Teacher portal JS
│       ├── practice.js           # Student practice JS
│       └── review_ai.js          # AI review interface JS
│
├── templates/                     # HTML templates
│   ├── login.html                # Login page
│   ├── register.html             # Registration
│   ├── teacher.html              # Teacher dashboard
│   ├── teacher_review_ai.html    # AI review interface
│   ├── practice.html             # Student practice
│   ├── student_dashboard.html    # Student home
│   └── ...                       # Other templates
│
├── Question Bank/                 # Question storage (auto-created)
│   └── [Subject]/
│       └── [Topic]/
│           └── [Subtopic]/
│               ├── [id]_question.md
│               ├── [id]_explanation.md
│               └── ...
│
├── Generated Papers/              # Paper outputs (auto-created)
│   └── [Timestamp]/
│       ├── paper_1.md
│       ├── paper_1.pdf
│       └── ...
│
└── tests/                         # Test files
    ├── test_evaluator.py
    ├── test_ai_answers.py
    └── ...
```

---

## 🗄️ Database Schema

### `teachers`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT (PK) | Username |
| password | TEXT | Hashed password |
| full_name | TEXT | Display name |
| email | TEXT | Contact email |
| created_at | TIMESTAMP | Account creation |

### `students`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT (PK) | Username |
| password | TEXT | Hashed password |
| full_name | TEXT | Display name |
| email | TEXT | Contact email |
| created_at | TIMESTAMP | Account creation |

### `questions`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Auto-incremented ID |
| title | TEXT | Question text |
| question_type | TEXT | MCQ, True/False, etc. |
| subject | TEXT | Subject name |
| topic | TEXT | Topic name |
| subtopic | TEXT | Subtopic name |
| difficulty_level | TEXT | Easy, Medium, Hard |
| estimated_time | INTEGER | Minutes |
| bloom_level | TEXT | Remember, Understand, etc. |
| teacher_id | INTEGER (FK) | Creator |
| has_explanation | BOOLEAN | Has explanation file |
| is_ai_generated | BOOLEAN | Generated by AI |
| parent_question_id | INTEGER (FK) | Original question (if variant) |
| accepted_by_teacher | BOOLEAN | Approval status |
| created_at | TIMESTAMP | Creation time |

### `question_answers`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Auto-incremented |
| question_id | INTEGER (FK) | Related question |
| correct_answer | TEXT | Answer/rubric |
| max_marks | REAL | Maximum score |
| total_attempts | INTEGER | Number of submissions |
| avg_scored | REAL | Average score |
| max_scored | REAL | Highest score |
| min_scored | REAL | Lowest score |

### `student_submissions`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Auto-incremented |
| student_id | TEXT (FK) | Student username |
| question_id | INTEGER (FK) | Question ID |
| submitted_answer | TEXT | Student's answer |
| score | REAL | Awarded score |
| max_marks | REAL | Possible score |
| submitted_at | TIMESTAMP | Submission time |

### `question_feedback`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Auto-incremented |
| question_id | INTEGER (FK) | Question ID |
| student_id | TEXT (FK) | Student username |
| is_question_clear | BOOLEAN | Clarity rating |
| is_answer_correct | BOOLEAN | Answer validity |
| is_difficulty_appropriate | BOOLEAN | Difficulty rating |
| overall_approval | BOOLEAN | Overall approval |
| additional_comments | TEXT | Free text feedback |
| created_at | TIMESTAMP | Feedback time |

---

## 🧪 Testing

### Run Unit Tests

```bash
# Test evaluator
python test_evaluator.py

# Test AI answer generation
python test_ai_answers.py

# Test feedback submission
python test_feedback_submission.py

# Test metrics
python test_metrics.py
```

### Manual Testing Checklist

- [ ] Teacher registration and login
- [ ] Student registration and login
- [ ] Add question with all types
- [ ] Generate AI variants
- [ ] Review and accept/reject AI questions
- [ ] Student answer submission
- [ ] Score display and feedback
- [ ] Answer and explanation reveal
- [ ] Generate papers (PDF + MD)
- [ ] Statistics tracking

---

## 🚀 Deployment

### Option 1: Local Server (Development)

```bash
python app.py
```

### Option 2: Gunicorn (Production)

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Option 3: Docker (Containerized)

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

Build and run:
```bash
docker build -t question-app .
docker run -p 8000:8000 --env-file .env question-app
```

### Environment-Specific Settings

**Development:**
- `FLASK_ENV=development`
- `FLASK_DEBUG=1`

**Production:**
- `FLASK_ENV=production`
- `FLASK_DEBUG=0`
- Use strong `SECRET_KEY`
- Enable HTTPS
- Use production database (PostgreSQL/MySQL)

---

## 🔒 Security Considerations

- ✅ **Password Hashing**: PBKDF2-SHA256 with salt
- ✅ **Session Security**: HTTP-only cookies, SameSite=Lax
- ✅ **CSRF Protection**: Built into Flask sessions
- ✅ **Role-Based Access**: Separate teacher/student decorators
- ⚠️ **API Key**: Store in .env, never commit to Git
- ⚠️ **SQL Injection**: Use parameterized queries
- ⚠️ **XSS Protection**: Sanitize user inputs

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 👥 Authors

- **Shubham Agrawal**
- **Vraj Shah**
- **Pranjal Gaur**
- **Dewansh Singh Chandel**

---

## 🙏 Acknowledgments

- **Groq** - AI model API
- **Flask** - Web framework
- **Bootstrap** - UI framework
- **MathJax** - LaTeX rendering
- **marked.js** - Markdown parsing

---

## 📞 Support

For issues and questions:
- **GitHub Issues**: [Create an issue](https://github.com/yourusername/question-paper-app/issues)
- **Email**: your.email@example.com

---

## 🗺️ Roadmap

- [ ] Multi-language support
- [ ] Image upload for questions
- [ ] Real-time collaboration
- [ ] Analytics dashboard
- [ ] Mobile app
- [ ] OAuth authentication
- [ ] Export to Word/Excel
- [ ] Question bank sharing

---



"""
Enhanced Paper Generation Module
Handles advanced question paper generation with multiple export formats
"""

import sqlite3
import random
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class EnhancedPaperGeneration:
    """Enhanced paper generation with multiple export formats"""

    def __init__(self, database_path: str):
        """Initialize paper generation"""
        self.database_path = database_path
        self.papers_folder = Path('Generated Papers')
        self.papers_folder.mkdir(exist_ok=True)

    def get_available_subjects(self) -> List[str]:
        """Get all available subjects from the database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute('SELECT DISTINCT subject FROM questions ORDER BY subject')
        subjects = [row[0] for row in cursor.fetchall()]

        conn.close()
        return subjects

    def get_topics_for_subject(self, subject: str) -> List[str]:
        """Get all topics for a given subject"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute('SELECT DISTINCT topic FROM questions WHERE subject = ? ORDER BY topic', (subject,))
        topics = [row[0] for row in cursor.fetchall()]

        conn.close()
        return topics

    def get_subtopics_for_topic(self, subject: str, topic: str) -> List[str]:
        """Get all subtopics for a given subject and topic"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT DISTINCT subtopic FROM questions
            WHERE subject = ? AND topic = ? AND subtopic IS NOT NULL AND subtopic != ""
            ORDER BY subtopic
        ''', (subject, topic))
        subtopics = [row[0] for row in cursor.fetchall()]

        conn.close()
        return subtopics
    
    def generate_paper(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a question paper based on criteria
        
        Args:
            criteria: Dictionary with generation criteria
            
        Returns:
            Response with generated paper data
        """
        try:
            total_questions = criteria.get('total_questions', 10)
            num_questions = criteria.get('num_questions', total_questions)
            
            print(f"Generating paper with {num_questions} questions")
            
            if num_questions <= 0:
                return {
                    'status': 'error',
                    'message': 'Total questions must be greater than 0'
                }
            
            # For now, just return success
            return {
                'status': 'success',
                'message': f'Paper will have {num_questions} questions'
            }
            
        except Exception as e:
            logger.error(f"Error generating paper: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error generating paper: {str(e)}'
            }
    
    def _build_query(self, criteria: Dict[str, Any]) -> tuple:
        """Build SQL query based on criteria"""
        conditions = []
        params = []
        
        # Subject filter
        if criteria.get('subjects'):
            placeholders = ','.join(['?' for _ in criteria['subjects']])
            conditions.append(f'subject IN ({placeholders})')
            params.extend(criteria['subjects'])
        
        # Topic filter
        if criteria.get('topics'):
            placeholders = ','.join(['?' for _ in criteria['topics']])
            conditions.append(f'topic IN ({placeholders})')
            params.extend(criteria['topics'])
        
        # Subtopic filter
        if criteria.get('subtopics'):
            placeholders = ','.join(['?' for _ in criteria['subtopics']])
            conditions.append(f'subtopic IN ({placeholders})')
            params.extend(criteria['subtopics'])
        
        # Question type filter
        if criteria.get('question_types'):
            placeholders = ','.join(['?' for _ in criteria['question_types']])
            conditions.append(f'question_type IN ({placeholders})')
            params.extend(criteria['question_types'])
        
        # Bloom level filter
        if criteria.get('bloom_levels'):
            placeholders = ','.join(['?' for _ in criteria['bloom_levels']])
            conditions.append(f'bloom_level IN ({placeholders})')
            params.extend(criteria['bloom_levels'])
        
        # AI generated filter
        if not criteria.get('include_ai_generated', True):
            conditions.append('is_ai_generated = 0')
        
        query = '''
            SELECT id, title, question_type, subject, topic, subtopic,
                   difficulty_level, estimated_time, bloom_level, is_ai_generated
            FROM questions
        '''
        
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        
        return query, params
    
    def _select_questions(self, questions: List[Dict], criteria: Dict[str, Any]) -> List[Dict]:
        """Select questions based on difficulty distribution and constraints"""
        total_questions = criteria.get('total_questions', 10)
        difficulty_dist = criteria.get('difficulty_distribution', {})
        max_time = criteria.get('max_time')
        
        selected = []
        
        if difficulty_dist:
            # Select by difficulty distribution
            for difficulty, count in difficulty_dist.items():
                diff_questions = [q for q in questions if q['difficulty_level'] == difficulty]
                random.shuffle(diff_questions)
                selected.extend(diff_questions[:count])
        else:
            # Random selection
            random.shuffle(questions)
            selected = questions[:total_questions]
        
        # Apply time constraint
        if max_time:
            selected = self._apply_time_constraint(selected, max_time)
        
        return selected[:total_questions]
    
    def _apply_time_constraint(self, questions: List[Dict], max_time: int) -> List[Dict]:
        """Filter questions to fit within time constraint"""
        questions.sort(key=lambda q: q['estimated_time'])
        
        selected = []
        total_time = 0
        
        for question in questions:
            if total_time + question['estimated_time'] <= max_time:
                selected.append(question)
                total_time += question['estimated_time']
        
        return selected
    
    def _generate_metadata(self, questions: List[Dict], criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Generate paper metadata"""
        if not questions:
            return {}
        
        total_time = sum(q['estimated_time'] for q in questions)
        
        difficulty_counts = {}
        type_counts = {}
        bloom_counts = {}
        subject_counts = {}
        
        for q in questions:
            diff = q['difficulty_level']
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
            
            qtype = q['question_type']
            type_counts[qtype] = type_counts.get(qtype, 0) + 1
            
            bloom = q['bloom_level']
            bloom_counts[bloom] = bloom_counts.get(bloom, 0) + 1
            
            subject = q['subject']
            subject_counts[subject] = subject_counts.get(subject, 0) + 1
        
        return {
            'total_questions': len(questions),
            'total_time_minutes': total_time,
            'difficulty_distribution': difficulty_counts,
            'question_type_distribution': type_counts,
            'bloom_level_distribution': bloom_counts,
            'subject_distribution': subject_counts,
            'ai_generated_count': sum(1 for q in questions if q['is_ai_generated']),
            'generated_at': datetime.now().isoformat()
        }
    
    def save_paper(self, paper_data: Dict[str, Any], filename: str,
                  format_type: str = 'markdown') -> Dict[str, Any]:
        """
        Save paper to file

        Args:
            paper_data: Paper data from generate_paper
            filename: Filename without extension
            format_type: 'markdown', 'json', or 'html'

        Returns:
            Response with file path
        """
        try:
            if format_type == 'markdown':
                file_path = self._save_as_markdown(paper_data, filename)
            elif format_type == 'json':
                file_path = self._save_as_json(paper_data, filename)
            elif format_type == 'html':
                file_path = self._save_as_html(paper_data, filename)
            else:
                return {
                    'status': 'error',
                    'message': f'Unsupported format: {format_type}'
                }

            return {
                'status': 'success',
                'message': 'Paper saved successfully',
                'file_path': file_path
            }

        except Exception as e:
            logger.error(f"Error saving paper: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error saving paper: {str(e)}'
            }

    def save_paper_to_file(self, paper_data: Dict[str, Any], filename: str,
                          format_type: str = 'markdown') -> str:
        """
        Legacy method for backward compatibility
        Saves paper to file and returns file path
        """
        if format_type == 'markdown':
            return self._save_as_markdown(paper_data, filename)
        elif format_type == 'json':
            return self._save_as_json(paper_data, filename)
        elif format_type == 'html':
            return self._save_as_html(paper_data, filename)
        else:
            raise ValueError(f'Unsupported format: {format_type}')
    
    def _save_as_markdown(self, paper_data: Dict[str, Any], filename: str) -> str:
        """Save paper as markdown"""
        file_path = self.papers_folder / f"{filename}.md"
        
        content = f"""# Question Paper

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Questions:** {paper_data['metadata']['total_questions']}
**Estimated Time:** {paper_data['metadata']['total_time_minutes']} minutes

---

## Paper Statistics

- **Difficulty Distribution:** {json.dumps(paper_data['metadata']['difficulty_distribution'])}
- **Question Types:** {json.dumps(paper_data['metadata']['question_type_distribution'])}
- **Bloom Levels:** {json.dumps(paper_data['metadata']['bloom_level_distribution'])}
- **AI Generated:** {paper_data['metadata']['ai_generated_count']}

---

## Questions

"""
        
        for i, q in enumerate(paper_data['questions'], 1):
            content += f"""### Question {i}

**Title:** {q['title']}
**Type:** {q['question_type']}
**Subject:** {q['subject']}
**Topic:** {q['topic']}
**Difficulty:** {q['difficulty_level']}
**Time:** {q['estimated_time']} minutes
**Bloom Level:** {q['bloom_level']}

---

"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(file_path)
    
    def _save_as_json(self, paper_data: Dict[str, Any], filename: str) -> str:
        """Save paper as JSON"""
        file_path = self.papers_folder / f"{filename}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(paper_data, f, indent=2)
        
        return str(file_path)
    
    def _save_as_html(self, paper_data: Dict[str, Any], filename: str) -> str:
        """Save paper as HTML"""
        file_path = self.papers_folder / f"{filename}.html"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Question Paper</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .metadata {{ background: #f5f5f5; padding: 10px; border-radius: 5px; }}
        .question {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007bff; }}
        .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    </style>
</head>
<body>
    <h1>Question Paper</h1>
    <div class="metadata">
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total Questions:</strong> {paper_data['metadata']['total_questions']}</p>
        <p><strong>Estimated Time:</strong> {paper_data['metadata']['total_time_minutes']} minutes</p>
    </div>
    
    <h2>Questions</h2>
"""
        
        for i, q in enumerate(paper_data['questions'], 1):
            html += f"""
    <div class="question">
        <h3>Question {i}: {q['title']}</h3>
        <p><strong>Type:</strong> {q['question_type']}</p>
        <p><strong>Subject:</strong> {q['subject']} | <strong>Topic:</strong> {q['topic']}</p>
        <p><strong>Difficulty:</strong> {q['difficulty_level']} | <strong>Time:</strong> {q['estimated_time']} min</p>
        <p><strong>Bloom Level:</strong> {q['bloom_level']}</p>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return str(file_path)
    
def generate_paper(subject, topics, difficulty, num_questions=10):
    """
    Generate paper with specified number of questions
    """
    console.print(f"[yellow]Generating paper with {num_questions} questions[/yellow]")


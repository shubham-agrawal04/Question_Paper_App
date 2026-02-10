
import unittest
import sqlite3
import os
import sys
from unittest.mock import patch, MagicMock

# Add local directory to path
sys.path.append(os.getcwd())

from app import app, init_database

class TestAnswerStorage(unittest.TestCase):
    
    def setUp(self):
        self.db_path = 'test_question_bank.db'
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Patch the DATABASE_PATH in app module
        self.db_patcher = patch('app.DATABASE_PATH', self.db_path)
        self.mock_db_path = self.db_patcher.start()
        
        # Initialize test database
        with patch('app.DATABASE_PATH', self.db_path):
            init_database()
            
    def tearDown(self):
        self.db_patcher.stop()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
    def get_question_answer(self, question_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT correct_answer FROM question_answers WHERE question_id = ?", (question_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def test_mcq_answer_storage(self):
        """Test storing answer for MCQ"""
        with patch('app.save_markdown_file', return_value='dummy/path.md'):
            response = self.client.post('/submit', data={
                'title': 'Test MCQ',
                'question_type': 'MCQ',
                'subject': 'Test Subject',
                'topic': 'Test Topic',
                'difficulty_level': 'Medium',
                'estimated_time': '5',
                'bloom_level': 'Recall',
                'full_question_text': 'Question text',
                'correct_answer': 'B'
            }, follow_redirects=True)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.get_question_answer(1), 'B')

    def test_coding_rubric_storage(self):
        """Test storing rubric for Coding question"""
        rubric_text = "Check for efficiency O(n). expected code: def foo()..."
        with patch('app.save_markdown_file', return_value='dummy/path.md'):
            response = self.client.post('/submit', data={
                'title': 'Test Coding',
                'question_type': 'Coding',
                'subject': 'CS',
                'topic': 'Algorithms',
                'difficulty_level': 'Hard',
                'estimated_time': '15',
                'bloom_level': 'Create',
                'full_question_text': 'Write a sort function',
                'answer_rubric': rubric_text
            }, follow_redirects=True)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.get_question_answer(1), rubric_text)

    def test_numerical_rubric_storage(self):
        """Test storing rubric for Numerical question"""
        answer_text = "42"
        with patch('app.save_markdown_file', return_value='dummy/path.md'):
            response = self.client.post('/submit', data={
                'title': 'Test Numerical',
                'question_type': 'Numerical',
                'subject': 'Math',
                'topic': 'Calc',
                'difficulty_level': 'Hard',
                'estimated_time': '10',
                'bloom_level': 'Apply',
                'full_question_text': 'What is 6*7?',
                'answer_rubric': answer_text
            }, follow_redirects=True)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.get_question_answer(1), answer_text)

if __name__ == '__main__':
    unittest.main()

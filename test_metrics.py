
import unittest
import sqlite3
import os
import sys
from unittest.mock import patch

# Add local directory to path
sys.path.append(os.getcwd())

from app import app, init_database

class TestQuestionMetrics(unittest.TestCase):
    
    def setUp(self):
        self.db_path = 'test_question_bank_metrics.db'
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
            
    def check_schema(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(question_answers)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return columns

    def get_question_metrics(self, question_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT max_marks, total_attempts FROM question_answers WHERE question_id = ?", (question_id,))
        result = cursor.fetchone()
        conn.close()
        return result

    def test_schema_update(self):
        """Test if metrics columns are added"""
        columns = self.check_schema()
        self.assertIn('max_marks', columns)
        self.assertIn('min_marks', columns)
        self.assertIn('max_scored', columns)
        self.assertIn('min_scored', columns)
        self.assertIn('avg_scored', columns)
        self.assertIn('total_attempts', columns)
        self.assertIn('avg_time_taken', columns)

    def test_save_max_marks(self):
        """Test storing max_marks for a question"""
        with patch('app.save_markdown_file', return_value='dummy/path.md'):
            response = self.client.post('/submit', data={
                'title': 'Test Metric Question',
                'question_type': 'Short Answer',
                'subject': 'Test Subject',
                'topic': 'Test Topic',
                'difficulty_level': 'Medium',
                'estimated_time': '5',
                'bloom_level': 'Understand',
                'full_question_text': 'Explain metrics.',
                'answer_rubric': 'Explanation...',
                'max_marks': '5.0'
            }, follow_redirects=True)
            
            self.assertEqual(response.status_code, 200)
            
            metrics = self.get_question_metrics(1)
            self.assertIsNotNone(metrics)
            self.assertEqual(metrics[0], 5.0) # max_marks
            self.assertEqual(metrics[1], 0)   # total_attempts (default)

if __name__ == '__main__':
    unittest.main()

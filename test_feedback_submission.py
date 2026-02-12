import unittest
import sqlite3
import os
import sys
import json

# Add local directory to path
sys.path.append(os.getcwd())

from app import app, init_database, DATABASE_PATH

class TestFeedbackSubmission(unittest.TestCase):
    
    def setUp(self):
        """Set up test database"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Initialize database
        init_database()
        
        # Create test user and login
        with self.app.test_request_context():
            from flask import session
            with self.client.session_transaction() as sess:
                sess['user_id'] = 'test_student'
                sess['role'] = 'student'
    
    def test_check_feedback_needed_for_ai_question(self):
        """Test feedback check for AI-generated pending question"""
        # Create a test AI question
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO questions (title, question_type, subject, topic, difficulty_level,
                                 estimated_time, bloom_level, is_ai_generated, acceptance_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Test AI Question', 'MCQ', 'Math', 'Algebra', 'Medium', 10, 'Apply', True, 'pending'))
        
        question_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Check if feedback is needed
        response = self.client.get(f'/api/check_feedback_needed/{question_id}')
        data = json.loads(response.data)
        
        self.assertTrue(data['needs_feedback'])
        self.assertEqual(data['acceptance_status'], 'pending')
        self.assertTrue(data['is_ai_generated'])
    
    def test_check_feedback_not_needed_for_original(self):
        """Test feedback check for original (non-AI) question"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO questions (title, question_type, subject, topic, difficulty_level,
                                 estimated_time, bloom_level, is_ai_generated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Original Question', 'MCQ', 'Math', 'Algebra', 'Medium', 10, 'Apply', False))
        
        question_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        response = self.client.get(f'/api/check_feedback_needed/{question_id}')
        data = json.loads(response.data)
        
        self.assertFalse(data['needs_feedback'])
    
    def test_submit_feedback(self):
        """Test submitting feedback for an AI question"""
        # Create test AI question
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO questions (title, question_type, subject, topic, difficulty_level,
                                 estimated_time, bloom_level, is_ai_generated, acceptance_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Test Question', 'MCQ', 'Math', 'Algebra', 'Medium', 10, 'Apply', True, 'pending'))
        
        question_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Submit feedback
        feedback_data = {
            'question_id': question_id,
            'is_question_clear': True,
            'is_answer_correct': True,
            'is_difficulty_appropriate': True,
            'additional_comments': 'Great question!'
        }
        
        response = self.client.post('/api/submit_feedback',
                                   data=json.dumps(feedback_data),
                                   content_type='application/json')
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('approval_ratio', data)
    
    def test_auto_acceptance_threshold(self):
        """Test auto-acceptance when 9/10 feedbacks are positive"""
        # Create test question
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO questions (title, question_type, subject, topic, difficulty_level,
                                 estimated_time, bloom_level, is_ai_generated, acceptance_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Test Question', 'MCQ', 'Math', 'Algebra', 'Medium', 10, 'Apply', True, 'pending'))
        
        question_id = cursor.lastrowid
        
        # Simulate 9 positive feedbacks
        for i in range(9):
            cursor.execute('''
                INSERT INTO question_feedback (question_id, student_id, is_question_clear,
                                             is_answer_correct, is_difficulty_appropriate,
                                             overall_approval)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (question_id, f'student_{i}', True, True, True, True))
        
        conn.commit()
        conn.close()
        
        # Submit 10th feedback (this should trigger auto-acceptance)
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'student_10'
        
        feedback_data = {
            'question_id': question_id,
            'is_question_clear': True,
            'is_answer_correct': True,
            'is_difficulty_appropriate': True
        }
        
        response = self.client.post('/api/submit_feedback',
                                   data=json.dumps(feedback_data),
                                   content_type='application/json')
        
        data = json.loads(response.data)
        self.assertTrue(data['auto_accepted'])
        
        # Verify question is now accepted
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT acceptance_status FROM questions WHERE id = ?', (question_id,))
        status = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(status, 'accepted')

if __name__ == '__main__':
    unittest.main()

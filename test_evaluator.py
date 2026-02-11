
import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add local directory to path
sys.path.append(os.getcwd())

from evaluator import Evaluator

class TestEvaluator(unittest.TestCase):
    def setUp(self):
        # We can use a dummy key for objective tests, 
        # but for subjective we might need to mock if no real key is present.
        self.api_key = os.getenv("GROQ_API_KEY") or "dummy_key"
        self.evaluator = Evaluator(api_key=self.api_key)

    def test_mcq_evaluation(self):
        """Test MCQ evaluation logic"""
        # Correct scenarios
        self.assertEqual(self.evaluator.evaluate('MCQ', 'A', 'A'), 5.0)
        self.assertEqual(self.evaluator.evaluate('MCQ', 'b', 'B'), 5.0) # Case insensitive
        
        # Incorrect scenarios
        self.assertEqual(self.evaluator.evaluate('MCQ', 'A', 'B'), 0.0)
        self.assertEqual(self.evaluator.evaluate('MCQ', 'C', 'A'), 0.0)

    def test_true_false_evaluation(self):
        """Test True/False evaluation logic"""
        # Correct scenarios
        self.assertEqual(self.evaluator.evaluate('True/False', 'True', 'True'), 5.0)
        self.assertEqual(self.evaluator.evaluate('True/False', 'T', 'True'), 5.0)
        self.assertEqual(self.evaluator.evaluate('True/False', 'yes', 'True'), 5.0)
        self.assertEqual(self.evaluator.evaluate('True/False', 'False', 'False'), 5.0)
        self.assertEqual(self.evaluator.evaluate('True/False', 'F', 'False'), 5.0)
        
        # Incorrect scenarios
        self.assertEqual(self.evaluator.evaluate('True/False', 'True', 'False'), 0.0)
        self.assertEqual(self.evaluator.evaluate('True/False', 'T', 'False'), 0.0)

    def test_fill_in_the_blank_evaluation(self):
        """Test Fill-in-the-blank evaluation logic"""
        # Correct scenarios
        self.assertEqual(self.evaluator.evaluate('Fill-in-the-blank', 'Photosynthesis', 'Photosynthesis'), 5.0)
        self.assertEqual(self.evaluator.evaluate('Fill-in-the-blank', ' photosynthesis ', 'Photosynthesis'), 5.0) # Trimming
        
        # Incorrect scenarios
        self.assertEqual(self.evaluator.evaluate('Fill-in-the-blank', 'Respiration', 'Photosynthesis'), 0.0)

    @patch('evaluator.Groq')
    def test_subjective_evaluation_mock(self, mock_groq):
        """Test subjective evaluation with mocked Groq API"""
        # Setup mock
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "4.5"
        
        mock_client.chat.completions.create.return_value = mock_completion
        mock_groq.return_value = mock_client
        
        # Re-initialize evaluator to use the mock
        evaluator = Evaluator(api_key="dummy")
        
        score = evaluator.evaluate('Short Answer', 'This is a good answer.', 'Rubric: Expect good answer.')
        
        # Check if score is parsed correctly
        self.assertEqual(score, 4.5)
        
        # Verify API was called
        mock_client.chat.completions.create.assert_called_once()
        
    def test_real_subjective_evaluation(self):
        """
        Test subjective evaluation with REAL Groq API if key is available.
        Skipped if no key found to avoid failure in CI/CD like environments without keys.
        """
        if not os.getenv("GROQ_API_KEY"):
            print("Skipping real API test: GROQ_API_KEY not found.")
            return

        print("\nTesting real Groq API for evaluation...")
        evaluator = Evaluator() # Uses env key
        
        student_ans = "The mitochondria is the powerhouse of the cell."
        rubric = "Correct answer should mention mitochondria and energy production or powerhouse."
        
        score = evaluator.evaluate('Short Answer', student_ans, rubric)
        print(f"Real API Score for '{student_ans}': {score}")
        
        self.assertTrue(0.0 <= score <= 5.0)

if __name__ == '__main__':
    unittest.main()

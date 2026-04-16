
import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add local directory to path
sys.path.append(os.getcwd())

from ai import QuestionGenerator

class TestAIAnswerGeneration(unittest.TestCase):
    
    def setUp(self):
        self.generator = QuestionGenerator(api_key="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")
    
    @patch('ai.Groq')
    def test_generate_answer_for_variant_mock(self, mock_groq):
        """Test answer generation with mocked Groq API"""
        # Setup mock
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = '{"answer": "B", "rubric": ""}'
        
        mock_client.chat.completions.create.return_value = mock_completion
        mock_groq.return_value = mock_client
        
        # Re-initialize generator with mock
        generator = QuestionGenerator(api_key="dummy")
        generator.client = mock_client
        
        original_q = "What is 2+2? A) 3 B) 4 C) 5 D) 6"
        original_a = "B"
        original_r = ""
        variant_q = "What is 3+3? A) 5 B) 6 C) 7 D) 8"
        
        answer = generator.generate_answer_for_variant(
            original_question=original_q,
            original_answer=original_a,
            original_rubric=original_r,
            ai_generated_question=variant_q,
            question_type="MCQ"
        )
        
        self.assertIn('"answer": "B"', answer)
        mock_client.chat.completions.create.assert_called_once()
        
    def test_real_answer_generation(self):
        """
        Test real AI answer generation if API key is available.
        This test demonstrates the actual workflow.
        """
        print("\nTesting real Groq API for answer generation...")
        
        # MCQ example
        original_q = """
        ### Question: Capital of France
        What is the capital of France?
        A) Berlin
        B) Paris  
        C) Madrid
        D) Rome
        """
        original_a = "B"
        original_r = ""
        
        variant_q = """
        ### Question: Capital of Germany
        What is the capital of Germany?
        A) Berlin
        B) Paris
        C) Madrid
        D) Rome
        """
        
        answer = self.generator.generate_answer_for_variant(
            original_question=original_q,
            original_answer=original_a,
            original_rubric=original_r,
            ai_generated_question=variant_q,
            question_type="MCQ"
        )
        
        print(f"Original question (France): Answer = {original_a}")
        print(f"Variant question (Germany): Generated Answer = {answer}")
        
        self.assertIsNotNone(answer)
        self.assertFalse(answer.startswith("Error"))
        
        # Coding example
        print("\n--- Testing Coding Question ---")
        original_coding = "Write a function to sort an array using bubble sort."
        original_a_coding = ""
        original_rubric = """
        Expected solution:
        - Implement nested loops
        - Compare adjacent elements
        - Swap if out of order
        - Time complexity O(n^2)
        """
        
        variant_coding = "Write a function to sort an array using selection sort."
        
        coding_answer = self.generator.generate_answer_for_variant(
            original_question=original_coding,
            original_answer=original_a_coding,
            original_rubric=original_rubric,
            ai_generated_question=variant_coding,
            question_type="Coding"
        )
        
        print(f"Original: Bubble sort")
        print(f"Variant: Selection sort")
        print(f"Generated rubric:\n{coding_answer}")
        
        self.assertIsNotNone(coding_answer)
        self.assertFalse(coding_answer.startswith("Error"))

if __name__ == '__main__':
    unittest.main()

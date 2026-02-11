
import os
import re
from typing import Union, Optional
from groq import Groq
from dotenv import load_dotenv

class Evaluator:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Evaluator with Groq API credentials.
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
             # Fallback to the key used in ai.py
             self.api_key = "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"
             
        self.client = Groq(api_key=self.api_key)
        self.model = "openai/gpt-oss-20b" # Using the same model as in ai.py

    def evaluate(self, question_type: str, student_answer: str, correct_answer_rubric: str) -> float:
        """
        Evaluate the student's answer against the correct answer or rubric.
        
        Args:
            question_type: The type of question (MCQ, True/False, etc.)
            student_answer: The answer provided by the student.
            correct_answer_rubric: The correct answer or grading rubric/key.
            
        Returns:
            A float score between 0.0 and 5.0.
        """
        if not student_answer:
            return 0.0

        # Normalize inputs
        q_type_norm = question_type.lower().strip()
        
        # Dispatch based on type
        if q_type_norm in ['mcq', 'true/false', 'fill-in-the-blank']:
            return self._evaluate_objective(q_type_norm, student_answer, correct_answer_rubric)
        else:
            return self._evaluate_subjective(question_type, student_answer, correct_answer_rubric)

    def _evaluate_objective(self, q_type: str, student_answer: str, correct_answer: str) -> float:
        """
        Evaluate objective questions using direct string/regex matching.
        Returns 5.0 for correct, 0.0 for incorrect.
        """
        # Normalize strings for comparison
        s_ans = student_answer.strip().lower()
        c_ans = correct_answer.strip().lower()
        
        # MCQ: Expect single letter usually, but handle full text if needed (user said regex)
        # We'll assume the student submits 'A', 'B', etc. or the full text.
        # But usually MCQs stored as 'A', 'B'.
        
        if q_type == 'mcq':
            # Strict match for option letters
            if s_ans == c_ans:
                return 5.0
            # Check if one is a substring of the other if checking text content (optional, sticking to strict for now)
            return 0.0
            
        elif q_type == 'true/false':
            # Handle T/F, True/False, Yes/No variatons
            truthy = ['true', 't', 'yes', 'y', '1']
            falsy = ['false', 'f', 'no', 'n', '0']
            
            s_bool = True if s_ans in truthy else (False if s_ans in falsy else None)
            c_bool = True if c_ans in truthy else (False if c_ans in falsy else None)
            
            if s_bool is not None and c_bool is not None:
                return 5.0 if s_bool == c_bool else 0.0
            
            # Fallback to string match
            return 5.0 if s_ans == c_ans else 0.0
            
        elif q_type == 'fill-in-the-blank':
            # Direct keyword match (case insensitive)
            if s_ans == c_ans:
                return 5.0
            return 0.0
            
        return 0.0

    def _evaluate_subjective(self, q_type: str, student_answer: str, rubric: str) -> float:
        """
        Evaluate subjective questions using AI.
        Returns a float between 0.0 and 5.0.
        """
        prompt = f"""
You are an expert academic evaluator. Your task is to grade a student's answer based on the provided rubric/correct answer key.

**Question Type:** {q_type}

**Rubric / Correct Answer / Evaluation Criteria:**
{rubric}

**Student Evaluation:**
{student_answer}

**Instructions:**
1. Compare the student's answer strictly against the rubric/answer key.
2. Assign a score from 0.0 to 5.0, where:
   - 0.0: Completely incorrect or irrelevant.
   - 5.0: Perfect, fully correct, matching all rubric criteria.
   - Use decimal values (e.g., 2.5, 3.8) for partial credit.
3. Be fair and consistent.
4. IMPORTANT: Your output must be ONLY the numeric score. Do not output any explanation, text, or markdown. Just the number.
"""
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise grading assistant. Output only the numerical score."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3, # Low temperature for consistency
                max_tokens=10
            )
            
            response_text = completion.choices[0].message.content.strip()
            
            # Extract number from response (in case AI is chatty)
            match = re.search(r"[-+]?\d*\.\d+|\d+", response_text)
            if match:
                score = float(match.group())
                # Clamp between 0 and 5
                return max(0.0, min(5.0, score))
            else:
                print(f"Error parsing AI score: {response_text}")
                return 0.0
                
        except Exception as e:
            print(f"AI Evaluation failed: {e}")
            return 0.0

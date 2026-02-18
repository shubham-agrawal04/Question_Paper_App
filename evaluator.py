
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
        prompt = f"""You are an expert academic evaluator for college-level Computer Science and Mathematics courses. Your task is to grade a student's answer based strictly on the provided rubric.

**Question Type:** {q_type}

**Rubric / Correct Answer / Evaluation Criteria:**
{rubric}

**Student's Answer:**
{student_answer}

## Few-Shot Grading Examples:

### Example 1 (Data Structures):
**Rubric:** "Explain Big-O notation. Should include: 1) Definition (upper bound) 2) Example (e.g., O(n²) for nested loops) 3) Why it matters (algorithm comparison)"
**Student Answer:** "Big-O describes worst-case time complexity. It's an upper bound on growth rate. For example, O(n) means linear time. Used to compare algorithms."
**Score:** 3.5
**Reasoning:** Has definition (1.5/2) and example (1/1.5), but example could be better. Missing analysis (1/1.5). Total: 3.5/5.0

### Example 2 (Algorithms):
**Rubric:** "Implement bubble sort. Code must: pass array, use nested loops, swap adjacent elements, return sorted array."
**Student Answer:**
```python
def bubble_sort(arr):
    for i in range(len(arr)):
        for j in range(len(arr)-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
```
**Score:** 5.0
**Reasoning:** Correct implementation with all required elements: takes array, nested loops, swaps adjacents, returns sorted. Perfect.

### Example 3 (Probability):
**Rubric:** "P(drawing 2 red balls) = (5/8) * (4/7) = 20/56 = 5/14. Must show: initial probability, conditional probability after first draw, final calculation."
**Student Answer:** "First ball: 5/8. Second ball: 4/7. Answer: 5/14"
**Score:** 4.0
**Reasoning:** Shows understanding of probabilities (2/2), shows final answer (1.5/1.5), but lacks explicit multiplication step (0.5/1.5). Total: 4.0/5.0

### Example 4 (Complexity Theory):
**Rubric:** "Master Theorem applies when T(n) = aT(n/b) + f(n). Case 1: f(n) = O(n^c) where c < log_b(a). Case 2: f(n) = Θ(n^c log^k n) where c = log_b(a). Case 3: f(n) = Ω(n^c) where c > log_b(a)."
**Student Answer:** "Master theorem has 3 cases based on comparing f(n) with n^(log_b a)."
**Score:** 1.5
**Reasoning:** Mentions 3 cases (0.5/2) and comparison concept (1/2), but missing all mathematical details and conditions (0/1). Total: 1.5/5.0

## Grading Instructions:

1. **Compare Against Rubric**: Evaluate ONLY what the rubric specifies. Don't penalize for missing unrelated content.

2. **Scoring Scale** (out of 5.0):
   - **5.0**: Perfect answer, meets all rubric criteria completely
   - **4.0-4.9**: Excellent, minor omissions or imprecisions
   - **3.0-3.9**: Good, covers main points but missing some detail or has minor errors
   - **2.0-2.9**: Satisfactory, partial understanding, missing key elements
   - **1.0-1.9**: Poor, minimal understanding, major gaps
   - **0.0-0.9**: Incorrect, irrelevant, or no meaningful content

3. **Partial Credit**: Award decimal scores (e.g., 2.5, 3.7) for partially correct answers

4. **Be Consistent**: Same quality answers should get same scores regardless of phrasing

## CRITICAL OUTPUT REQUIREMENT:
Output ONLY a single numeric value between 0.0 and 5.0.
DO NOT include explanations, reasoning, text, or any other content.
DO NOT say "Score:", "The grade is", or similar phrases.
JUST THE NUMBER. Example outputs: 4.5 or 3.0 or 5.0

Your Score:"""
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise grading assistant. Output ONLY a single numeric score between 0.0 and 5.0. No text, no explanations, JUST THE NUMBER."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2, # Very low temperature for consistency
                max_tokens=10
            )
            
            response_text = completion.choices[0].message.content.strip()
            
            # Extract number from response (in case AI is chatty)
            match = re.search(r"[-+]?\d*\.?\d+", response_text)
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

from typing import Dict, Any, Optional
import os
from groq import Groq
from dotenv import load_dotenv

class QuestionGenerator:
    def __init__(self, api_key: str = os.getenv("GROQ_API_KEY"), model: str = "openai/gpt-oss-20b"):
        """
        Initialize the Question Generator with Groq API credentials
        
        Args:
            api_key: Groq API key
            model: Model to use (default: openai/gpt-oss-20b)
        """
        self.client = Groq(api_key=api_key)
        self.model = model
    
    def generate_question_prompt(self, 
                               question_markdown: str, 
                               difficulty: str, 
                               bloom_level: str, 
                               has_parameters: bool, 
                               parameters_info: Optional[Dict[str, Dict[str, Any]]] = None, 
                               additional_notes: str = "") -> str:
        """
        Generate a structured prompt for the LLM based on question metadata
        
        Args:
            question_markdown: Original question content in markdown
            difficulty: Difficulty level (e.g., Easy, Medium, Hard)
            bloom_level: Bloom's taxonomy level (e.g., Remember, Understand, Apply, Analyze, Evaluate, Create)
            has_parameters: Whether the question has variable parameters
            parameters_info: Dictionary containing parameter ranges/constraints
            additional_notes: Special instructions for question generation
        
        Returns:
            Formatted prompt string for the LLM
        """
        prompt = f"""You are an expert question generator for college-level educational assessments. Your task is to create a unique question variant that maintains the same difficulty level and educational objectives as the provided template.

## Original Question Template:
{question_markdown}

## Metadata:
- **Difficulty**: {difficulty}
- **Bloom's Level**: {bloom_level}
- **Has Variable Parameters**: {'Yes' if has_parameters else 'No'}
"""
        
        if has_parameters and parameters_info:
            prompt += "\n## Parameter Specifications:\n"
            for param_name, param_details in parameters_info.items():
                if 'min' in param_details and 'max' in param_details:
                    prompt += f"- **{param_name}**: Range [{param_details['min']}, {param_details['max']}]\n"
                elif 'values' in param_details:
                    prompt += f"- **{param_name}**: Options: {param_details['values']}\n"
                elif 'type' in param_details:
                    prompt += f"- **{param_name}**: Type: {param_details['type']}\n"
        
        if additional_notes:
            prompt += f"\n## Additional Instructions:\n{additional_notes}\n"
        
        prompt += """
## Few-Shot Examples:

### Example 1 (Algorithm Analysis):
**Original:** "Analyze the time complexity of the following pseudocode using Big-O notation: for i=1 to n: for j=1 to n: for k=1 to j: print(i+j+k)"
**Generated Variant:** "Determine the time complexity in Big-O notation for this algorithm: for x=1 to m: for y=1 to x: for z=1 to m: sum += x*y*z"

### Example 2 (Probability):
**Original:** "A bag contains 5 red balls and 3 blue balls. What is the probability of drawing 2 red balls without replacement?"
**Generated Variant:** "An urn has 7 green marbles and 4 yellow marbles. Calculate the probability of selecting 2 green marbles consecutively without replacement."

### Example 3 (Data Structures):
**Original:** "Explain why a binary search tree with n nodes has average search time O(log n) but worst-case O(n)."
**Generated Variant:** "Describe why AVL trees guarantee O(log n) search time in all cases, unlike standard binary search trees that can degrade to O(n)."

### Example 4 (Discrete Math):
**Original:** "Prove that for all integers n ≥ 1, the sum 1 + 2 + 3 + ... + n = n(n+1)/2 using mathematical induction."
**Generated Variant:** "Use mathematical induction to prove that for all positive integers k, the sum of first k odd numbers equals k²."

## Generation Rules:
1. **Maintain Difficulty**: Keep the same cognitive load and complexity
2. **Preserve Concept**: Change values/context but keep the core learning objective
3. **Follow Constraints**: Respect all parameter specifications
4. **Use LaTeX**: For mathematical expressions, use LaTeX notation (e.g., $O(n^2)$, $\\frac{n(n+1)}{2}$)
5. **College-Level**: Assume undergraduate CS/Math/Engineering knowledge

## CRITICAL OUTPUT REQUIREMENT:
Return ONLY the generated question text in Markdown format with LaTeX for math.
DO NOT include any preamble, explanations, metadata, or commentary.
DO NOT say "Here is the generated question" or similar phrases.
START IMMEDIATELY with the question content.

Generated Question:"""
        return prompt
    
    def generate_question(self, 
                         question_markdown: str, 
                         difficulty: str, 
                         bloom_level: str, 
                         has_parameters: bool = False, 
                         parameters_info: Optional[Dict[str, Dict[str, Any]]] = None, 
                         additional_notes: str = "",
                         temperature: float = 0.7,
                         max_tokens: int = 500) -> str:
        """
        Generate a question using the Groq API
        
        Args:
            question_markdown: Original question in markdown format
            difficulty: Difficulty level
            bloom_level: Bloom's taxonomy level
            has_parameters: Whether question has parameters
            parameters_info: Parameter specifications
            additional_notes: Additional generation notes
            temperature: Randomness control (0.0-1.0)
            max_tokens: Maximum response length
        
        Returns:
            Generated question text
        """
        try:
            # Generate the prompt
            prompt = self.generate_question_prompt(
                question_markdown, difficulty, bloom_level, 
                has_parameters, parameters_info, additional_notes
            )
            
            # Call the Groq API
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": f"You are an expert educational question generator focused on creating diverse, high-quality assessment questions.\n\n{prompt}"
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1,
                stream=False,
                stop=None
            )
            
            # Extract and return the generated question
            generated_question = completion.choices[0].message.content.strip()
            return generated_question
            
        except Exception as e:
            return f"Error generating question: {str(e)}"
    
    def generate_multiple_questions(self, 
                                  question_markdown: str, 
                                  difficulty: str, 
                                  bloom_level: str, 
                                  count: int = 5,
                                  has_parameters: bool = False, 
                                  parameters_info: Optional[Dict[str, Dict[str, Any]]] = None, 
                                  additional_notes: str = "") -> list:
        """
        Generate multiple unique questions based on the same template
        
        Returns:
            List of generated questions
        """
        questions = []
        for i in range(count):
            question = self.generate_question(
                question_markdown, difficulty, bloom_level, 
                has_parameters, parameters_info, additional_notes,
                temperature=0.8  # Higher temperature for more variety
            )
            questions.append(question)
        return questions
    
    def generate_answer_for_variant(self,
                                   original_question: str,
                                   original_answer: str,
                                   ai_generated_question: str,
                                   question_type: str) -> str:
        """
        Generate the correct answer/rubric for an AI-generated question variant
        based on the original question and its answer.
        
        Args:
            original_question: The original question text
            original_answer: The correct answer/rubric for the original question
            ai_generated_question: The AI-generated variant question
            question_type: Type of question (MCQ, Coding, etc.)
            
        Returns:
            Generated answer/rubric for the variant question
        """
        prompt = f"""You are an expert educational assessment developer specializing in creating answer keys and grading rubrics for college-level courses.

## TASK:
Generate the correct answer/rubric for an AI-generated variant question by analyzing the relationship between the original question and its answer.

## ORIGINAL QUESTION:
{original_question}

## ORIGINAL ANSWER/RUBRIC:
{original_answer}

## AI-GENERATED VARIANT QUESTION:
{ai_generated_question}

## QUESTION TYPE: {question_type}

## Few-Shot Examples:

### Example 1 (Data Structures - Short Answer):
**Original Q:** "Explain the difference between a stack and a queue in terms of data access patterns."
**Original A:** "Stack follows LIFO (Last-In-First-Out) principle where the most recently added element is removed first. Queue follows FIFO (First-In-First-Out) where the oldest element is removed first. Example: Stack is like a stack of plates, Queue is like a waiting line."

**Variant Q:** "Compare and contrast the access patterns of heaps and priority queues."
**Generated A:** "Heap is a tree-based data structure where parent nodes have specific ordering relationships with children (min-heap or max-heap). Priority queue is an abstract data type where elements are served based on priority, often implemented using heaps. Both allow prioritized access, but heaps provide O(log n) insertion/deletion while maintaining structural properties."

### Example 2 (Algorithms - Coding):
**Original Q:** "Write a Python function to implement binary search on a sorted array."
**Original A:**
```python
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

**Variant Q:** "Implement linear search in Python for an unsorted list."
**Generated A:**
```python
def linear_search(lst, target):
    for i in range(len(lst)):
        if lst[i] == target:
            return i
    return -1
```

### Example 3 (Probability - MCQ):
**Original Q:** "What is P(A ∪ B) if P(A) = 0.3, P(B) = 0.4, P(A ∩ B) = 0.1? (A) 0.5 (B) 0.6 (C) 0.7 (D) 0.8"
**Original A:** "B"

**Variant Q:** "Calculate P(X ∪ Y) given P(X) = 0.25, P(Y) = 0.35, P(X ∩ Y) = 0.05? (A) 0.45 (B) 0.50 (C) 0.55 (D) 0.60"
**Generated A:** "C"

### Example 4 (Complexity Analysis - Descriptive):
**Original Q:** "Analyze the time complexity of merge sort and explain why it's O(n log n)."
**Original A:** "Merge sort divides array into halves recursively (log n levels) and merges them (O(n) per level). Total: O(n log n). Works by: 1) Divide array into two halves 2) Recursively sort each half 3) Merge sorted halves in O(n) time. Recurrence: T(n) = 2T(n/2) + O(n) → O(n log n) by Master Theorem."

**Variant Q:** "Explain the time complexity of quicksort and why average case is O(n log n)."
**Generated A:** "Quicksort partitions array around pivot (O(n) per level) across log n average levels. Total: O(n log n) average. Works by: 1) Choose pivot element 2) Partition array into elements < pivot and > pivot 3) Recursively sort partitions. Average case has balanced partitions giving log n depth. Worst case O(n²) occurs with poor pivot selection (e.g., sorted input)."

## CRITICAL INSTRUCTIONS:

1. **Match Structure**: Your answer MUST follow the same structure, format, and level of detail as the original answer
2. **Preserve Style**: If original uses bullet points, use bullet points. If it has code blocks, include code blocks. If it's a single letter, respond with a single letter.
3. **Maintain Complexity**: Keep the same depth of explanation and technical rigor
4. **Question Type Guidelines**:
   - **MCQ**: Return ONLY the option letter (A/B/C/D) that is correct
   - **True/False**: Return ONLY "True" or "False"
   - **Fill-in-the-blank**: Return ONLY the exact word/phrase expected
   - **Coding**: Provide complete, working code with same structure as original
   - **Short Answer**: Match paragraph structure and key points format
   - **Descriptive**: Include same number of points/sections with equivalent detail

5. **Output Format**: Return ONLY the answer/rubric content. NO preambles like "The answer is..." or "Here is the solution...". START IMMEDIATELY with the answer content.

Generated Answer/Rubric:"""
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise educational content generator. Output only the requested answer/rubric matching the original's structure exactly. No commentary or explanations about the answer itself."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=1000,
                top_p=1,
                stream=False,
                stop=None
            )
            
            generated_answer = completion.choices[0].message.content.strip()
            return generated_answer
            
        except Exception as e:
            return f"Error generating answer: {str(e)}"


def generate_ai_response(prompt):
    """Generate AI response using Groq"""
    client = Groq(api_key="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")
    
    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=1,
        max_tokens=8192,
        top_p=1,
        reasoning_effort="medium",
        stream=True,
        stop=None
    )
    
    response = ""
    for chunk in completion:
        content = chunk.choices[0].delta.content or ""
        response += content
    
    return response

# Example usage
def main():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    # Initialize with Groq (API key is now default)
    generator = QuestionGenerator(api_key=api_key)
    
    # Example 1: Math question with parameters
    math_question = """
    ## Rectangle Area Problem
    Calculate the area of a rectangle with length **L** meters and width **W** meters.
    Show your work and express the answer in square meters.
    """
    
    math_params = {
        "L": {"min": 5, "max": 25, "type": "integer"},
        "W": {"min": 3, "max": 20, "type": "integer"}
    }
    
    generated_math = generator.generate_question(
        question_markdown=math_question,
        difficulty="Medium",
        bloom_level="Apply",
        has_parameters=True,
        parameters_info=math_params,
        additional_notes="Use only whole numbers. Ensure the problem can be solved in 2-3 steps. Include units in the final answer."
    )
    
    print("Generated Math Question:")
    print(generated_math)
    print("\n" + "="*50 + "\n")
    
    # Example 2: Science question without parameters
    science_question = """
    ## Photosynthesis Process
    Explain the role of chlorophyll in photosynthesis and describe how it contributes to energy conversion in plants.
    """
    
    generated_science = generator.generate_question(
        question_markdown=science_question,
        difficulty="Hard",
        bloom_level="Analyze",
        has_parameters=False,
        additional_notes="Focus on biochemical processes. Require students to connect molecular-level events to broader ecological impacts."
    )
    
    print("Generated Science Question:")
    print(generated_science)
    print("\n" + "="*50 + "\n")
    
    # Example 3: Generate multiple variations
    multiple_questions = generator.generate_multiple_questions(
        question_markdown=math_question,
        difficulty="Medium",
        bloom_level="Apply",
        count=3,
        has_parameters=True,
        parameters_info=math_params,
        additional_notes="Vary the context (garden, room, field, etc.) while maintaining the same mathematical concept."
    )
    
    print("Multiple Generated Questions:")
    for i, q in enumerate(multiple_questions, 1):
        print(f"{i}. {q}\n")

if __name__ == "__main__":
    main()

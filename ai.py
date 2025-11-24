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
        prompt = f"""You are an expert question generator for educational assessments. Your task is to create a unique question that maintains the same difficulty level and educational objectives as the provided template.

## Original Question Template (Markdown):
{question_markdown}

## Question Metadata:
- **Difficulty Level**: {difficulty}
- **Bloom's Taxonomy Level**: {bloom_level}
- **Has Variable Parameters**: {'Yes' if has_parameters else 'No'}
"""
        
        if has_parameters and parameters_info:
            prompt += "\n## Parameter Specifications:\n"
            for param_name, param_details in parameters_info.items():
                if 'min' in param_details and 'max' in param_details:
                    prompt += f"- **{param_name}**: Range from {param_details['min']} to {param_details['max']}\n"
                elif 'values' in param_details:
                    prompt += f"- **{param_name}**: Possible values: {param_details['values']}\n"
                elif 'type' in param_details:
                    prompt += f"- **{param_name}**: Type: {param_details['type']}\n"
        
        if additional_notes:
            prompt += f"\n## Additional Instructions:\n{additional_notes}\n"
        
        prompt += """
## Task:
Generate ONE unique question that:
1. Maintains the same difficulty level and Bloom's taxonomy level
2. Uses different specific values/contexts while preserving the core concept
3. Follows all parameter constraints if applicable
4. Adheres to any additional instructions provided
5. Is clearly written and educationally sound

Provide only the generated question without explanations or metadata.
"""
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

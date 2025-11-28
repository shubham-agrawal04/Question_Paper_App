# Question Bank Management System

A comprehensive web-based question management application built with Python (Flask) that helps teachers create, manage, and generate question papers, while allowing students to practice and improve their skills.

## Overview

This application simplifies the process of managing educational assessments by providing intuitive tools for question tracking, AI-powered generation, and automated paper creation. Whether you're a teacher organizing exams or a student preparing for tests, this application makes it easy to handle the entire assessment lifecycle.

## Key Features

### 1. Teacher Management
*   **Question Management**: Create, edit, view, and delete questions with detailed metadata.
*   **Markdown Support**: Write questions using Markdown with real-time preview.
*   **AI Generation**: Generate similar questions automatically using AI models.
*   **Analytics**: View statistics about the question bank distribution.

### 2. Student Practice
*   **Browse Questions**: Navigate through subjects, topics, and subtopics.
*   **Practice Mode**: Attempt questions with immediate feedback.
*   **Random Practice**: Generate random question sets for self-assessment.
*   **Progress Tracking**: Monitor practice sessions and improvement.

### 3. Automated Paper Generation
Create professional question papers with flexible criteria:
*   **Custom Selection**: Choose specific subjects, topics, and subtopics.
*   **Difficulty Distribution**: Set percentage for Easy, Medium, and Hard questions.
*   **PDF Export**: Automatically generate and download formatted PDF papers.

### 4. AI & Intelligence
*   **Smart Variations**: Generate unique variants of existing questions using Groq AI.
*   **Bloom's Taxonomy**: Categorize questions by cognitive levels (Recall to Create).
*   **Context Preservation**: AI maintains the core concept while changing values/context.

### 5. User Management
*   **Role-Based Access**: Distinct portals for Teachers and Students.
*   **Secure Authentication**: Session-based login system.
*   **Dashboard Views**: Customized dashboards for different user roles.

## Technology Stack

*   **Backend**: Python with Flask web framework
*   **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
*   **Database**: SQLite
*   **AI Engine**: Groq API (LLM Integration)
*   **PDF Generation**: WeasyPrint

## Getting Started

### Prerequisites
*   Python 3.8+
*   pip (Python package manager)
*   Groq API Key (Change in .env file)

### Installation

1.  Clone or download the project.

2.  Install required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Run the application:
    ```bash
    python app.py
    ```

4.  Open your browser and navigate to `http://localhost:5001`

## Usage

### Logging In
*   **Teacher**: Username `teacher`, Password `teacher123`
*   **Student**: Username `student`, Password `student123`

### Managing Questions
*   **Add Question**: Use the teacher dashboard to create new questions with metadata.
*   **AI Generation**: Select a question and generate variants using the AI tool.
*   **Organize**: Questions are automatically sorted into Subject/Topic folders.

### Generating Papers
*   **Configure**: Select criteria (Subject, Difficulty, Marks).
*   **Generate**: Create the paper and view the generated PDF.
*   **Download**: Save the PDF for printing or distribution.

## Features Highlights

*   ✨ **AI-Powered** - Generate unique question variants automatically
*   📊 **Visual Analytics** - Insights into question distribution
*   🔄 **Real-Time Preview** - Live Markdown rendering for questions
*   📄 **PDF Export** - Professional question paper generation
*   🎯 **Smart Filtering** - Advanced search and filter options
*   📱 **Responsive Design** - Works seamlessly on different screen sizes

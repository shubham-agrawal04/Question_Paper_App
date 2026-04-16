# New Features (Since Baseline)

Compared against the baseline `PROJECT_WALKTHROUGH.md`. Only features that did **not exist before** are listed here.

---

## 1. Student Answer Submission & AI Evaluation

At baseline the student workflow was marked as *"currently limited to dashboard view"*. Now fully implemented:

- Students can open any question, write an answer, and submit
- **Objective types** (MCQ, True/False, Fill-in-the-blank) are graded by exact match
- **Subjective types** (Short Answer, Descriptive, Coding) are graded by the AI on a 0–5 rubric with partial credit
- Score, correct answer, and explanation are shown immediately after submission
- MathJax renders LaTeX in questions and answers

---

## 2. AI Answer & Rubric Generation

At baseline the AI only generated question variants. Now:

- For every AI-generated question variant, the system automatically generates a matching answer key or rubric
- Output mirrors the original answer's format (single letter for MCQ, code block for coding, etc.)

---

## 3. AI Question Review Workflow

No review mechanism existed at baseline — AI variants went directly to the question bank. Now:

- AI-generated variants go into a **pending review queue**
- Teachers review each variant, then approve (adds to question bank) or reject it
- Prevents unreviewed AI content from reaching students

---

## 4. Explanation Editor

Did not exist at baseline:

- Teachers can write a detailed explanation for any question
- Explanation is shown to the student after they submit their answer
- Supports full Markdown and LaTeX formatting

---

## 5. Per-Question Statistics Tracking

Did not exist at baseline:

- Each question tracks: total attempts, average score, min score, max score, average time taken
- Teacher dashboard shows aggregate stats: total questions, subjects covered, topics covered, AI-generated count

---

## 6. AI Prompt Engineering

At baseline the AI generation used a basic prompt with no examples. Now:

- **College-level few-shot examples** added to question generation, answer generation, and grading prompts
- **Strict output formatting** enforced (LaTeX-only math, structure-matching answers, numeric-only scores)
- Lower AI temperature for more consistent, predictable output

---

## 7. Teacher Portal UI Redesign

At baseline navigation was partial and inconsistent across pages. Now:

- **Uniform 5-tab navigation** on every teacher page (Dashboard, Add Question, Manage Question Bank, Create Paper, Review AI Questions)
- **Dashboard** redesigned with 5 clickable feature cards (was 2) with hover animations
- **Dashboard is now the landing page** after login (previously went to Add Question)
- **Dark theme applied consistently** across all teacher pages

---

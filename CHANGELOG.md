# CHANGELOG — Question Paper Generation & Management System

> Detailed before/after comparison against the baseline `PROJECT_WALKTHROUGH.md`.

---

## 1. Student Answer Submission & AI Evaluation

**Before:** Student workflow was explicitly marked *"currently limited to dashboard view"* — students could log in but had no way to interact with questions or submit answers.

**After:**

- Students can open any question from their portal and write an answer in a text area
- **Objective types** (MCQ, True/False, Fill-in-the-blank) are graded instantly via exact/normalised string matching
- **Subjective types** (Short Answer, Descriptive, Coding) are sent to the Groq AI which grades them on a strict 0.0–5.0 rubric with partial credit
- After submission, the student sees: their score, max marks, percentage, the correct answer/rubric, and any explanation if one exists
- Scores are stored in `student_submissions` table; per-question aggregate stats (avg, min, max, total attempts) are updated in `question_answers`
- MathJax renders LaTeX in both questions and answer feedback

**Files changed:** `app.py` (`/api/student/submit_answer`, `/api/student/get_explanation`), `evaluator.py`, `templates/practice.html`

---

## 2. AI Answer & Rubric Generation

**Before:** The AI only generated question variant text. No answer key or rubric was generated for AI variants — teachers had to write answers manually.

**After:**

- For every AI-generated question variant, the system automatically calls the AI to generate a matching answer key or rubric
- The AI is given the original question, original answer, and the new variant; it infers the correct answer by analogy
- Output format strictly mirrors the original: single letter for MCQ, full code block for coding questions, bullet points for structured answers
- Temperature lowered to 0.3 for consistency; output preambles stripped

**Files changed:** `ai.py` (`generate_answer_for_variant()`)

---

## 3. AI Question Review Workflow

**Before:** AI-generated question variants were added directly to the question bank with no review step. Teachers had no way to inspect or reject AI output before it became part of the bank.

**After:**

- All AI-generated variants are saved with `acceptance_status = 'pending'` and `educator_reviewed = False`
- A dedicated **Review AI Questions** page lists all pending variants
- Teachers can read the variant, its AI-generated answer, and then **approve** (status → `accepted`, added to active bank) or **reject** (status → `rejected`, hidden from students)
- A 5th navigation tab links to this page from every teacher portal page

**Files changed:** `app.py` (review routes), `templates/teacher_review_ai.html`

---

## 4. Explanation Editor

**Before:** No mechanism existed for teachers to attach explanations to questions, and students saw no post-answer feedback beyond the score.

**After:**

- Teachers can navigate to any question and write a detailed explanation using a full Markdown + LaTeX editor
- Explanation is stored as a separate `.md` file alongside the question (`{id}_explanation.md`) and flagged in the DB (`has_explanation = True`)
- After a student submits an answer, if an explanation exists it is fetched and displayed in the feedback modal
- MathJax renders any LaTeX in the explanation

**Files changed:** `app.py` (`/teacher/edit_explanation/<id>`), `templates/edit_explanation.html`, `templates/practice.html`

---

## 5. Per-Question Statistics Tracking

**Before:** The `question_answers` table existed but `total_attempts`, `avg_scored`, `max_scored`, `min_scored` were never populated — there was no submission pipeline to update them.

**After:**

- Every student submission triggers an UPDATE on `question_answers` recalculating avg/min/max scored and incrementing `total_attempts`
- Teachers can expand the **Statistics** section on any question card in Manage Question Bank to see these live stats
- The teacher dashboard header shows aggregate counts: total questions, subjects, topics, and AI-generated question count (loaded via `/questions` API on page load)

**Files changed:** `app.py` (submit answer route, stats aggregation), `templates/manage_questions.html`, `templates/teacher_dashboard.html`

---

## 6. AI Prompt Engineering

**Before:** All three AI functions (question generation, answer generation, grading) used a single basic prompt with no examples. Output format was inconsistently followed, math expressions were plain text, and grading scores sometimes included explanatory text instead of a clean number.

**After:**

| Function | Before | After |
|---|---|---|
| Question generation | Basic instruction prompt | + 4 college-level few-shot examples; LaTeX enforced for all math; no preamble output rule |
| Answer generation | Basic instruction prompt | + 4 format-matched examples (MCQ/Code/Short/Descriptive); structure-mirroring enforced; temperature → 0.3 |
| Student grading | Basic rubric comparison | + 4 grading examples with scores and reasoning; strict 0.0–5.0 numeric-only output; temperature → 0.2 |

**Files changed:** `ai.py` (`generate_question_prompt()`, `generate_answer_for_variant()`), `evaluator.py` (`_evaluate_subjective()`)

---

## 7. Teacher Portal UI Redesign

**Before:** Navigation was partial and inconsistent — tabs varied page to page, some pages lacked a dark background, and logging in sent teachers to the Add Question form.

**After:**

| Aspect | Before | After |
|---|---|---|
| Navigation tabs | 2–4 tabs, different per page | Exactly 5 tabs on every page |
| Tab set | Varied | Dashboard · Add Question · Manage Question Bank · Create Paper · Review AI Questions |
| Tab alignment | Right-aligned (`ms-auto`) | Left-aligned (`me-auto`); user menu separated right |
| Dashboard cards | 2 cards (Add Question, Create Paper) | 5 cards with icons, descriptions, hover lift animation |
| Landing page after login | Add Question page (`/teacher`) | Dashboard (`/teacher/dashboard`) |
| Dark theme coverage | Missing on Manage & Review AI pages | Applied uniformly via `style.css` on all teacher pages |
| Stats section | Included a nested "View Papers" card | Removed (redundant — already a top-level feature card) |

**Files changed:** `app.py` (index + login redirects), `templates/teacher_dashboard.html`, `templates/teacher.html`, `templates/manage_questions.html`, `templates/create_paper.html`, `templates/teacher_review_ai.html`, `static/css/style.css`

---

## Summary of All Files Modified

| File | Reason |
|---|---|
| `app.py` | Login redirect, student submission API, stats update, explanation routes, review routes |
| `ai.py` | Enhanced prompts for question and answer generation |
| `evaluator.py` | Enhanced grading prompt with few-shot examples and strict output |
| `templates/teacher_dashboard.html` | 5-tab nav, 5 feature cards, removed redundant button |
| `templates/teacher.html` | Uniform 5-tab navigation |
| `templates/manage_questions.html` | Dark theme + 5-tab navigation |
| `templates/create_paper.html` | Uniform 5-tab navigation |
| `templates/teacher_review_ai.html` | Dark theme + 5-tab navigation |
| `templates/practice.html` | Student answer submission, score modal, explanation display |
| `templates/edit_explanation.html` | New page — explanation editor for teachers |
| `static/css/style.css` | `.hover-card` animation class added |

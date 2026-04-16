// Student Practice Interface JavaScript

// Global variables
let currentQuestions = [];
let currentSelection = {
    subject: null,
    topic: null,
    subtopic: null
};

// Session tracking
let practiceSession = {
    active: false,
    startTime: null,
    attempts: []  // { questionId, title, score, maxMarks, percentage, subject, topic, difficulty, questionType }
};

document.addEventListener('DOMContentLoaded', function () {
    // Initialize the practice interface
    loadQuestionTree();
});

/**
 * Load the question tree structure
 */
async function loadQuestionTree() {
    try {
        const response = await fetch('/api/practice/tree');
        const result = await response.json();

        if (result.status === 'success') {
            renderQuestionTree(result.tree);
            document.getElementById('loading-tree').style.display = 'none';
            document.getElementById('question-tree').style.display = 'block';
        } else {
            showError('Failed to load question tree: ' + result.message);
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    }
}

/**
 * Render the question tree in the sidebar
 */
function renderQuestionTree(tree) {
    const container = document.getElementById('question-tree');
    container.innerHTML = '';

    for (const [subject, topics] of Object.entries(tree)) {
        const subjectElement = createTreeNode(subject, 'subject', () => {
            // Subject click - could expand/collapse
        });

        const topicsContainer = document.createElement('div');
        topicsContainer.className = 'ms-3';

        for (const [topic, subtopics] of Object.entries(topics)) {
            const topicElement = createTreeNode(topic, 'topic', () => {
                // Topic click - could expand/collapse
            });

            const subtopicsContainer = document.createElement('div');
            subtopicsContainer.className = 'ms-3';

            for (const [subtopic, count] of Object.entries(subtopics)) {
                const subtopicElement = createTreeNode(
                    `${subtopic} (${count})`,
                    'subtopic',
                    () => loadQuestions(subject, topic, subtopic)
                );
                subtopicsContainer.appendChild(subtopicElement);
            }

            topicElement.appendChild(subtopicsContainer);
            topicsContainer.appendChild(topicElement);
        }

        subjectElement.appendChild(topicsContainer);
        container.appendChild(subjectElement);
    }
}

/**
 * Create a tree node element
 */
function createTreeNode(text, type, clickHandler) {
    const node = document.createElement('div');
    node.className = `tree-node tree-${type} p-2 mb-1 rounded`;

    const icon = getIconForType(type);
    node.innerHTML = `<i class="bi ${icon} me-2"></i>${text}`;

    if (type === 'subtopic') {
        node.style.cursor = 'pointer';
        node.addEventListener('click', () => {
            // Remove active class from all nodes
            document.querySelectorAll('.tree-node').forEach(n => n.classList.remove('active'));
            // Add active class to clicked node
            node.classList.add('active');
            clickHandler();
        });

        node.addEventListener('mouseenter', () => {
            if (!node.classList.contains('active')) {
                node.style.backgroundColor = 'rgba(88, 166, 255, 0.1)';
            }
        });

        node.addEventListener('mouseleave', () => {
            if (!node.classList.contains('active')) {
                node.style.backgroundColor = '';
            }
        });
    }

    return node;
}

/**
 * Get icon for tree node type
 */
function getIconForType(type) {
    switch (type) {
        case 'subject': return 'bi-book';
        case 'topic': return 'bi-bookmark';
        case 'subtopic': return 'bi-bookmark-fill';
        default: return 'bi-circle';
    }
}

/**
 * Load questions for selected category
 */
async function loadQuestions(subject, topic, subtopic) {
    try {
        // Update current selection
        currentSelection = { subject, topic, subtopic };

        // Show loading
        showWelcomeMessage(false);
        showQuestionList(false);
        showQuestionDetail(false);

        const params = new URLSearchParams({
            subject: subject,
            topic: topic,
            subtopic: subtopic
        });

        const response = await fetch(`/api/practice/questions?${params}`);
        const result = await response.json();

        if (result.status === 'success') {
            currentQuestions = result.questions;
            renderQuestionList(result.questions, subject, topic, subtopic);
            showQuestionList(true);
        } else {
            showError('Failed to load questions: ' + result.message);
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    }
}

/**
 * Render the question list
 */
function renderQuestionList(questions, subject, topic, subtopic) {
    const container = document.getElementById('questions-container');
    const countBadge = document.getElementById('question-count-badge');

    countBadge.textContent = `${questions.length} question${questions.length !== 1 ? 's' : ''}`;

    container.innerHTML = `
        <div class="mb-3">
            <h6><i class="bi bi-folder"></i> ${subject} > ${topic} > ${subtopic}</h6>
        </div>
    `;

    if (questions.length === 0) {
        container.innerHTML += `
            <div class="text-center text-muted">
                <i class="bi bi-inbox display-4"></i>
                <p class="mt-2">No questions found in this category.</p>
            </div>
        `;
        return;
    }

    questions.forEach((question, index) => {
        const questionCard = document.createElement('div');
        questionCard.className = 'card mb-3 question-card';
        questionCard.style.cursor = 'pointer';

        questionCard.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="card-title">${question.title}</h6>
                        <div class="row">
                            <div class="col-md-6">
                                <small class="text-muted">
                                    <i class="bi bi-tag"></i> ${question.question_type}
                                </small>
                            </div>
                            <div class="col-md-6">
                                <small class="text-muted">
                                    <i class="bi bi-speedometer2"></i> ${question.difficulty_level}
                                </small>
                            </div>
                        </div>
                        <div class="row mt-1">
                            <div class="col-md-6">
                                <small class="text-muted">
                                    <i class="bi bi-clock"></i> ${question.estimated_time} min
                                </small>
                            </div>
                            <div class="col-md-6">
                                <small class="text-muted">
                                    <i class="bi bi-diagram-3"></i> ${question.bloom_level}
                                </small>
                            </div>
                        </div>
                    </div>
                    <div class="ms-3">
                        <i class="bi bi-arrow-right text-primary"></i>
                    </div>
                </div>
            </div>
        `;

        questionCard.addEventListener('click', () => loadQuestionDetail(question.id));

        questionCard.addEventListener('mouseenter', () => {
            questionCard.style.transform = 'translateY(-2px)';
            questionCard.style.boxShadow = '0 4px 15px rgba(0, 0, 0, 0.1)';
        });

        questionCard.addEventListener('mouseleave', () => {
            questionCard.style.transform = '';
            questionCard.style.boxShadow = '';
        });

        container.appendChild(questionCard);
    });
}

/**
 * Load and display question detail
 */
async function loadQuestionDetail(questionId) {
    try {
        const response = await fetch(`/api/practice/question/${questionId}`);
        const result = await response.json();

        if (result.status === 'success') {
            renderQuestionDetail(result.question);
            showQuestionDetail(true);
            showQuestionList(false);
        } else {
            showError('Failed to load question: ' + result.message);
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    }
}

/**
 * Render question detail view
 */
function renderQuestionDetail(question) {
    // Start session if not already started
    if (!practiceSession.active) {
        practiceSession.active = true;
        practiceSession.startTime = new Date();
        practiceSession.attempts = [];
    }

    // Show end practice button
    const endPracticeNav = document.getElementById('end-practice-nav');
    if (endPracticeNav) endPracticeNav.style.display = 'block';

    document.getElementById('question-title').textContent = question.title;

    // Update badges in header
    document.getElementById('question-type-badge').textContent = question.question_type;
    document.getElementById('difficulty-badge').textContent = question.difficulty_level;

    // Update metadata fields
    document.getElementById('question-subject').textContent = currentSelection.subject || question.subject || 'N/A';
    document.getElementById('question-topic').textContent = currentSelection.topic || question.topic || 'N/A';
    document.getElementById('question-time-detail').textContent = question.estimated_time;
    document.getElementById('question-bloom-detail').textContent = question.bloom_level;

    // Render markdown content
    const contentContainer = document.getElementById('question-content');
    try {
        const htmlContent = marked.parse(question.content);
        contentContainer.innerHTML = htmlContent;
        // Render LaTeX with MathJax
        if (window.MathJax) {
            MathJax.typesetPromise([contentContainer]).catch(err => console.error('MathJax error:', err));
        }
    } catch (error) {
        contentContainer.innerHTML = `<div class="alert alert-danger">Error rendering question content: ${error.message}</div>`;
    }

    // Clear previous answer
    document.getElementById('student-answer').value = '';

    // Setup answer buttons with question ID
    setupAnswerButtons(question.id);
}

/**
 * Setup answer submission buttons
 */
function setupAnswerButtons(questionId) {
    const submitBtn = document.getElementById('submit-answer-btn');
    const clearBtn = document.getElementById('clear-answer-btn');
    const answerTextarea = document.getElementById('student-answer');

    // Remove old event listeners by cloning and replacing
    const newSubmitBtn = submitBtn.cloneNode(true);
    submitBtn.parentNode.replaceChild(newSubmitBtn, submitBtn);

    const newClearBtn = clearBtn.cloneNode(true);
    clearBtn.parentNode.replaceChild(newClearBtn, clearBtn);

    // Add new event listeners
    newSubmitBtn.addEventListener('click', async () => {
        const answer = answerTextarea.value.trim();
        if (answer === '') {
            alert('Please write an answer before submitting.');
            return;
        }

        // Show loading state
        newSubmitBtn.disabled = true;
        const originalText = newSubmitBtn.innerHTML;
        newSubmitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Evaluating...';

        try {
            // Call evaluation API
            const response = await fetch('/api/student/submit_answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question_id: questionId,
                    student_answer: answer
                })
            });

            const result = await response.json();

            if (result.status === 'success') {
                // Track this attempt in session
                const titleEl = document.getElementById('question-title');
                const subjectEl = document.getElementById('question-subject');
                const topicEl = document.getElementById('question-topic');
                const diffBadge = document.getElementById('difficulty-badge');
                const typeBadge = document.getElementById('question-type-badge');

                practiceSession.attempts.push({
                    questionId: questionId,
                    title: titleEl ? titleEl.textContent : 'Unknown',
                    score: result.score,
                    maxMarks: result.max_marks,
                    percentage: result.percentage,
                    subject: subjectEl ? subjectEl.textContent : 'Unknown',
                    topic: topicEl ? topicEl.textContent : 'Unknown',
                    difficulty: diffBadge ? diffBadge.textContent : 'Unknown',
                    questionType: typeBadge ? typeBadge.textContent : 'Unknown'
                });

                // Show score modal
                showScoreModal(result, answer, questionId);
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        } finally {
            // Reset button
            newSubmitBtn.disabled = false;
            newSubmitBtn.innerHTML = originalText;
        }
    });

    newClearBtn.addEventListener('click', () => {
        answerTextarea.value = '';
        answerTextarea.focus();
    });
}

/**
 * Show score modal with results
 */
function showScoreModal(result, studentAnswer, questionId) {
    // Update score display
    document.getElementById('score-value').textContent = result.score;
    document.getElementById('max-marks-value').textContent = result.max_marks;
    document.getElementById('percentage-value').textContent = result.percentage.toFixed(0) + '%';

    // Update progress bar
    const progressBar = document.getElementById('score-progress-bar');
    progressBar.style.width = result.percentage + '%';
    progressBar.setAttribute('aria-valuenow', result.percentage);

    // Color code progress bar
    if (result.percentage >= 80) {
        progressBar.className = 'progress-bar bg-success';
        document.getElementById('score-message').textContent = 'Excellent work! 🎉';
    } else if (result.percentage >= 60) {
        progressBar.className = 'progress-bar bg-info';
        document.getElementById('score-message').textContent = 'Good job! Keep it up! 👍';
    } else if (result.percentage >= 40) {
        progressBar.className = 'progress-bar bg-warning';
        document.getElementById('score-message').textContent = 'Not bad! Room for improvement. 💪';
    } else {
        progressBar.className = 'progress-bar bg-danger';
        document.getElementById('score-message').textContent = 'Keep practicing! You\'ll get better! 📚';
    }

    // Display student's answer
    document.getElementById('student-answer-display').textContent = studentAnswer;

    // Setup correct answer reveal
    const showAnswerBtn = document.getElementById('show-answer-btn');
    const correctAnswerSection = document.getElementById('correct-answer-section');
    const correctAnswerDisplay = document.getElementById('correct-answer-display');

    // Clone button to remove old listeners
    const newShowAnswerBtn = showAnswerBtn.cloneNode(true);
    showAnswerBtn.parentNode.replaceChild(newShowAnswerBtn, showAnswerBtn);

    newShowAnswerBtn.addEventListener('click', () => {
        if (correctAnswerSection.style.display === 'none') {
            // Render answer as markdown
            const answerHtml = marked.parse(result.correct_answer);
            correctAnswerDisplay.innerHTML = answerHtml;

            // Render LaTeX
            if (window.MathJax) {
                MathJax.typesetPromise([correctAnswerDisplay]).catch(err => console.error('MathJax error:', err));
            }

            correctAnswerSection.style.display = 'block';
            newShowAnswerBtn.innerHTML = '<i class="bi bi-eye-slash"></i> Hide Correct Answer';
        } else {
            correctAnswerSection.style.display = 'none';
            newShowAnswerBtn.innerHTML = '<i class="bi bi-eye"></i> Show Correct Answer/Rubric';
        }
    });

    // Reset to hidden state
    correctAnswerSection.style.display = 'none';
    newShowAnswerBtn.innerHTML = '<i class="bi bi-eye"></i> Show Correct Answer/Rubric';

    // Check for explanation
    fetch(`/api/student/get_explanation/${questionId}`)
        .then(response => response.json())
        .then(data => {
            const explanationContainer = document.getElementById('explanation-container');

            if (data.status === 'success' && data.has_explanation) {
                explanationContainer.style.display = 'block';

                const showExplanationBtn = document.getElementById('show-explanation-btn');
                const explanationSection = document.getElementById('explanation-section');
                const explanationDisplay = document.getElementById('explanation-display');

                // Clone button to remove old listeners
                const newShowExplanationBtn = showExplanationBtn.cloneNode(true);
                showExplanationBtn.parentNode.replaceChild(newShowExplanationBtn, showExplanationBtn);

                newShowExplanationBtn.addEventListener('click', () => {
                    if (explanationSection.style.display === 'none') {
                        // Render explanation as markdown
                        const explanationHtml = marked.parse(data.explanation);
                        explanationDisplay.innerHTML = explanationHtml;

                        // Render LaTeX
                        if (window.MathJax) {
                            MathJax.typesetPromise([explanationDisplay]).catch(err => console.error('MathJax error:', err));
                        }

                        explanationSection.style.display = 'block';
                        newShowExplanationBtn.innerHTML = '<i class="bi bi-lightbulb-off"></i> Hide Explanation';
                    } else {
                        explanationSection.style.display = 'none';
                        newShowExplanationBtn.innerHTML = '<i class="bi bi-lightbulb"></i> Show Explanation';
                    }
                });

                // Reset to hidden state
                explanationSection.style.display = 'none';
                newShowExplanationBtn.innerHTML = '<i class="bi bi-lightbulb"></i> Show Explanation';
            } else {
                explanationContainer.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error fetching explanation:', error);
            document.getElementById('explanation-container').style.display = 'none';
        });

    // Setup "Try Another Question" button
    const tryAnotherBtn = document.getElementById('try-another-btn');
    const newTryAnotherBtn = tryAnotherBtn.cloneNode(true);
    tryAnotherBtn.parentNode.replaceChild(newTryAnotherBtn, tryAnotherBtn);

    newTryAnotherBtn.addEventListener('click', () => {
        const modal = bootstrap.Modal.getInstance(document.getElementById('scoreModal'));
        modal.hide();
        goBackToList();
    });

    // Show the modal
    const scoreModal = new bootstrap.Modal(document.getElementById('scoreModal'));
    scoreModal.show();
}

/**
 * Go back to question list
 */
function goBackToList() {
    showQuestionDetail(false);
    showQuestionList(true);
}

/**
 * Show/hide welcome message
 */
function showWelcomeMessage(show) {
    document.getElementById('welcome-message').style.display = show ? 'block' : 'none';
}

/**
 * Show/hide question list
 */
function showQuestionList(show) {
    document.getElementById('question-list').style.display = show ? 'block' : 'none';
}

/**
 * Show/hide question detail
 */
function showQuestionDetail(show) {
    document.getElementById('question-detail').style.display = show ? 'block' : 'none';
}

/**
 * Show error message
 */
function showError(message) {
    // You could implement a toast notification or modal here
    console.error(message);
    alert(message); // Simple fallback
}

/**
 * End Practice Session - compute and display stats
 */
function endPracticeSession() {
    const attempts = practiceSession.attempts;
    const now = new Date();
    const sessionStart = practiceSession.startTime || now;
    const durationMs = now - sessionStart;
    const durationMin = Math.floor(durationMs / 60000);
    const durationSec = Math.floor((durationMs % 60000) / 1000);

    // Session duration
    document.getElementById('session-duration').textContent = `${durationMin}m ${durationSec}s`;

    if (attempts.length === 0) {
        // No attempts - show minimal stats
        document.getElementById('stat-total-attempted').textContent = '0';
        document.getElementById('stat-correct').textContent = '0';
        document.getElementById('stat-partial').textContent = '0';
        document.getElementById('stat-incorrect').textContent = '0';
        document.getElementById('stat-accuracy').textContent = '0%';
        document.getElementById('accuracy-bar').style.width = '0%';
        document.getElementById('stat-total-score').textContent = '0 / 0';
        document.getElementById('stat-best-score').textContent = '\u2014';
        document.getElementById('stat-worst-score').textContent = '\u2014';
        document.getElementById('stat-topics-breakdown').innerHTML = '<p class="text-muted mb-0">No topics practiced yet.</p>';
        document.getElementById('stat-difficulty-breakdown').innerHTML = '<p class="text-muted mb-0">No data available.</p>';
    } else {
        // Compute stats
        const totalAttempted = attempts.length;
        const correct = attempts.filter(a => a.percentage >= 80).length;
        const partial = attempts.filter(a => a.percentage >= 40 && a.percentage < 80).length;
        const incorrect = attempts.filter(a => a.percentage < 40).length;

        const totalScore = attempts.reduce((sum, a) => sum + a.score, 0);
        const totalMaxMarks = attempts.reduce((sum, a) => sum + a.maxMarks, 0);
        const overallAccuracy = totalMaxMarks > 0 ? (totalScore / totalMaxMarks * 100) : 0;

        const bestAttempt = attempts.reduce((best, a) => a.percentage > best.percentage ? a : best, attempts[0]);
        const worstAttempt = attempts.reduce((worst, a) => a.percentage < worst.percentage ? a : worst, attempts[0]);

        document.getElementById('stat-total-attempted').textContent = totalAttempted;
        document.getElementById('stat-correct').textContent = correct;
        document.getElementById('stat-partial').textContent = partial;
        document.getElementById('stat-incorrect').textContent = incorrect;
        document.getElementById('stat-accuracy').textContent = overallAccuracy.toFixed(1) + '%';
        document.getElementById('accuracy-bar').style.width = overallAccuracy.toFixed(1) + '%';
        document.getElementById('stat-total-score').textContent = `${totalScore.toFixed(1)} / ${totalMaxMarks.toFixed(1)}`;
        document.getElementById('stat-best-score').textContent = `${bestAttempt.percentage.toFixed(0)}% (${bestAttempt.title.substring(0, 30)}${bestAttempt.title.length > 30 ? '...' : ''})`;
        document.getElementById('stat-worst-score').textContent = `${worstAttempt.percentage.toFixed(0)}% (${worstAttempt.title.substring(0, 30)}${worstAttempt.title.length > 30 ? '...' : ''})`;

        // Topic breakdown
        const topicMap = {};
        attempts.forEach(a => {
            const key = `${a.subject} > ${a.topic}`;
            if (!topicMap[key]) {
                topicMap[key] = { count: 0, totalScore: 0, totalMax: 0 };
            }
            topicMap[key].count++;
            topicMap[key].totalScore += a.score;
            topicMap[key].totalMax += a.maxMarks;
        });

        let topicsHtml = '';
        for (const [topic, stats] of Object.entries(topicMap)) {
            const topicAccuracy = stats.totalMax > 0 ? (stats.totalScore / stats.totalMax * 100) : 0;
            const barColor = topicAccuracy >= 80 ? '#3fb950' : topicAccuracy >= 40 ? '#d29922' : '#f85149';
            topicsHtml += `
                <div class="mb-2">
                    <div class="d-flex justify-content-between">
                        <small>${topic}</small>
                        <small>${stats.count} Q &bull; ${topicAccuracy.toFixed(0)}%</small>
                    </div>
                    <div class="progress" style="height: 6px; background: #30363d;">
                        <div class="progress-bar" style="width: ${topicAccuracy}%; background: ${barColor};"></div>
                    </div>
                </div>
            `;
        }
        document.getElementById('stat-topics-breakdown').innerHTML = topicsHtml || '<p class="text-muted mb-0">No topics practiced yet.</p>';

        // Difficulty breakdown
        const diffMap = {};
        attempts.forEach(a => {
            const key = a.difficulty || 'Unknown';
            if (!diffMap[key]) {
                diffMap[key] = { count: 0, totalScore: 0, totalMax: 0 };
            }
            diffMap[key].count++;
            diffMap[key].totalScore += a.score;
            diffMap[key].totalMax += a.maxMarks;
        });

        let diffHtml = '';
        const diffColors = { 'Easy': '#3fb950', 'Medium': '#d29922', 'Hard': '#f85149' };
        for (const [diff, stats] of Object.entries(diffMap)) {
            const diffAccuracy = stats.totalMax > 0 ? (stats.totalScore / stats.totalMax * 100) : 0;
            const color = diffColors[diff] || '#58a6ff';
            diffHtml += `
                <div class="d-inline-block me-3 mb-2">
                    <span class="badge" style="background: ${color}; font-size: 0.85em;">
                        ${diff}: ${stats.count} Q &bull; ${diffAccuracy.toFixed(0)}%
                    </span>
                </div>
            `;
        }
        document.getElementById('stat-difficulty-breakdown').innerHTML = diffHtml || '<p class="text-muted mb-0">No data available.</p>';
    }

    // Show the modal
    const sessionModal = new bootstrap.Modal(document.getElementById('sessionSummaryModal'));
    sessionModal.show();

    // Reset session
    practiceSession.active = false;
    practiceSession.startTime = null;
    practiceSession.attempts = [];

    // Hide the end practice button
    const endPracticeNav = document.getElementById('end-practice-nav');
    if (endPracticeNav) endPracticeNav.style.display = 'none';
}

// Add CSS for tree nodes and question cards
const style = document.createElement('style');
style.textContent = `
    .tree-node {
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }
    
    .tree-node.active {
        background-color: rgba(88, 166, 255, 0.2) !important;
        border-color: #58a6ff;
    }
    
    .tree-subject {
        font-weight: 600;
        color: #58a6ff;
    }
    
    .tree-topic {
        font-weight: 500;
        color: #79c0ff;
    }
    
    .tree-subtopic {
        color: #e6edf3;
    }
    
    .question-card {
        transition: all 0.3s ease;
        border: 1px solid #30363d;
    }
    
    .question-card:hover {
        border-color: #58a6ff;
    }
`;
document.head.appendChild(style);

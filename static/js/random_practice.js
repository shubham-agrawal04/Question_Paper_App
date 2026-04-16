// Random Practice JavaScript
let selectedTopics = [];
let currentQuestion = null;
let practiceStarted = false;

// Session tracking
let practiceSession = {
    active: false,
    startTime: null,
    attempts: []  // { questionId, title, score, maxMarks, percentage, subject, topic, difficulty, questionType }
};

document.addEventListener('DOMContentLoaded', function() {
    loadTopics();
    setupEventListeners();
});



function setupEventListeners() {
    // Select all topics checkbox
    document.getElementById('select-all-topics').addEventListener('change', function() {
        const isChecked = this.checked;
        const topicCheckboxes = document.querySelectorAll('.topic-checkbox');
        
        topicCheckboxes.forEach(checkbox => {
            checkbox.checked = isChecked;
        });
        
        updateSelectedTopics();
    });
    
    // Start practice button
    document.getElementById('start-practice-btn').addEventListener('click', startPracticeSession);
    
    // Next question button
    document.getElementById('next-question-btn').addEventListener('click', loadNextQuestion);
    
    // End session button
    document.getElementById('end-session-btn').addEventListener('click', endPracticeSession);
    
    // Submit answer button
    document.getElementById('submit-answer-btn').addEventListener('click', submitAnswer);
    
    // Clear answer button
    document.getElementById('clear-answer-btn').addEventListener('click', function() {
        document.getElementById('student-answer').value = '';
    });
}

function loadTopics() {
    fetch('/api/practice/topics')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayTopics(data.topics);
            } else {
                showError('Failed to load topics: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error loading topics:', error);
            showError('Error loading topics. Please try again.');
        });
}

function displayTopics(topics) {
    const container = document.getElementById('topics-container');
    
    // Group topics by subject
    const topicsBySubject = {};
    topics.forEach(topic => {
        if (!topicsBySubject[topic.subject]) {
            topicsBySubject[topic.subject] = [];
        }
        topicsBySubject[topic.subject].push(topic);
    });
    
    let html = '';
    Object.keys(topicsBySubject).forEach(subject => {
        html += `
            <div class="mb-4">
                <h6 class="text-primary fw-bold">${subject}</h6>
                <div class="row">
        `;
        
        topicsBySubject[subject].forEach(topic => {
            const topicId = `${topic.subject}:${topic.topic}`;
            html += `
                <div class="col-md-6 mb-2">
                    <div class="form-check">
                        <input class="form-check-input topic-checkbox" type="checkbox" 
                               id="topic-${topicId.replace(/[^a-zA-Z0-9]/g, '_')}" 
                               value="${topicId}">
                        <label class="form-check-label" for="topic-${topicId.replace(/[^a-zA-Z0-9]/g, '_')}">
                            ${topic.topic} 
                            <span class="badge bg-secondary">${topic.question_count}</span>
                        </label>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    
    // Add event listeners to topic checkboxes
    document.querySelectorAll('.topic-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedTopics);
    });
}

function updateSelectedTopics() {
    const selectAllCheckbox = document.getElementById('select-all-topics');
    const topicCheckboxes = document.querySelectorAll('.topic-checkbox');
    const startButton = document.getElementById('start-practice-btn');
    
    selectedTopics = [];
    
    if (selectAllCheckbox.checked) {
        selectedTopics = ['all'];
    } else {
        topicCheckboxes.forEach(checkbox => {
            if (checkbox.checked) {
                selectedTopics.push(checkbox.value);
            }
        });
    }
    
    // Enable/disable start button
    startButton.disabled = selectedTopics.length === 0;
}

function startPracticeSession() {
    practiceStarted = true;
    
    // Start session tracking
    practiceSession.active = true;
    practiceSession.startTime = new Date();
    practiceSession.attempts = [];
    
    // Hide topic selection and show practice session
    document.getElementById('topic-selection').style.display = 'none';
    document.getElementById('practice-session').style.display = 'block';
    
    // Load first question
    loadNextQuestion();
}

function loadNextQuestion() {
    console.log('Loading next question...'); // Debug log

    // Set a timeout to show error if request takes too long (10 seconds)
    const requestTimeout = setTimeout(() => {
        console.warn('Request timeout');
        showError('Request timed out. Please try again.');
    }, 10000);

    // Build query parameters
    const params = new URLSearchParams();
    selectedTopics.forEach(topic => {
        params.append('topics', topic);
    });

    console.log('Fetching question with params:', params.toString());

    fetch(`/api/practice/random-question?${params.toString()}`)
        .then(response => {
            clearTimeout(requestTimeout); // Clear timeout on response
            console.log('Response received:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Data received:', data);

            if (data.status === 'success') {
                currentQuestion = data.question;
                displayQuestion(currentQuestion);
                clearAnswer();
            } else {
                showError('Failed to load question: ' + data.message);
            }
        })
        .catch(error => {
            clearTimeout(requestTimeout); // Clear timeout on error
            console.error('Error loading question:', error);
            showError('Error loading question. Please try again.');
        });
}

function displayQuestion(question) {
    try {
        console.log('Displaying question:', question); // Debug log

        // Update question metadata
        document.getElementById('current-question-title').textContent = question.title || 'Untitled Question';
        document.getElementById('question-type-badge').textContent = question.question_type || 'Unknown';
        document.getElementById('difficulty-badge').textContent = question.difficulty_level || 'Unknown';
        document.getElementById('question-subject').textContent = question.subject || 'Unknown';
        document.getElementById('question-topic').textContent = question.topic || 'Unknown';
        document.getElementById('question-time').textContent = question.estimated_time || '0';
        document.getElementById('question-bloom').textContent = question.bloom_level || 'Unknown';

        // Render question content
        const contentDiv = document.getElementById('question-content');
        if (question.content && question.content.trim()) {
            try {
                contentDiv.innerHTML = marked.parse(question.content);
                // Render LaTeX with MathJax
                if (window.MathJax) {
                    MathJax.typesetPromise([contentDiv]).catch(err => console.error('MathJax error:', err));
                }
            } catch (markdownError) {
                console.error('Markdown parsing error:', markdownError);
                contentDiv.innerHTML = `<pre>${question.content}</pre>`;
            }
        } else {
            contentDiv.innerHTML = '<p class="text-muted">No content available for this question.</p>';
        }

        console.log('Question displayed successfully'); // Debug log
    } catch (error) {
        console.error('Error displaying question:', error);
        showError('Error displaying question content.');
    }
}

function submitAnswer() {
    const answer = document.getElementById('student-answer').value.trim();
    
    if (!answer) {
        alert('Please enter an answer before submitting.');
        return;
    }
    
    if (!currentQuestion) {
        alert('No question loaded.');
        return;
    }
    
    const submitBtn = document.getElementById('submit-answer-btn');
    submitBtn.disabled = true;
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Evaluating...';
    
    // Call evaluation API
    fetch('/api/student/submit_answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            question_id: currentQuestion.id,
            student_answer: answer
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            // Track this attempt
            practiceSession.attempts.push({
                questionId: currentQuestion.id,
                title: currentQuestion.title || 'Unknown',
                score: result.score,
                maxMarks: result.max_marks,
                percentage: result.percentage,
                subject: currentQuestion.subject || 'Unknown',
                topic: currentQuestion.topic || 'Unknown',
                difficulty: currentQuestion.difficulty_level || 'Unknown',
                questionType: currentQuestion.question_type || 'Unknown'
            });
            
            // Show score feedback
            const pct = result.percentage.toFixed(0);
            let emoji = pct >= 80 ? '🎉' : pct >= 60 ? '👍' : pct >= 40 ? '💪' : '📚';
            alert(`Score: ${result.score}/${result.max_marks} (${pct}%) ${emoji}\n\nClick "Next Question" to continue.`);
        } else {
            alert('Error evaluating answer: ' + (result.error || result.message));
        }
    })
    .catch(error => {
        console.error('Error submitting answer:', error);
        alert('Error submitting answer. Please try again.');
    })
    .finally(() => {
        submitBtn.disabled = true; // Keep disabled until next question
        submitBtn.innerHTML = originalText;
        document.getElementById('next-question-btn').focus();
    });
}

function clearAnswer() {
    document.getElementById('student-answer').value = '';
    document.getElementById('submit-answer-btn').disabled = false;
}

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

    // Reset state
    practiceStarted = false;
    practiceSession.active = false;
    practiceSession.startTime = null;
    practiceSession.attempts = [];
    
    // Show topic selection and hide practice session
    document.getElementById('practice-session').style.display = 'none';
    document.getElementById('topic-selection').style.display = 'block';
    
    // Reset selections
    document.getElementById('select-all-topics').checked = false;
    document.querySelectorAll('.topic-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
    
    selectedTopics = [];
    currentQuestion = null;
    updateSelectedTopics();
}

function showError(message) {
    // Create and show an alert
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.innerHTML = `
        <i class="bi bi-exclamation-triangle"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Insert at the top of the container
    const container = document.querySelector('.container-fluid');
    container.insertBefore(alertDiv, container.firstChild);

    // Auto-dismiss after 8 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 8000);
}

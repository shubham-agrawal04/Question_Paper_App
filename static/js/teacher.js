// Teacher Question Bank Form JavaScript

document.addEventListener('DOMContentLoaded', function () {
    // Get form elements
    const form = document.getElementById('questionForm');
    const markdownInput = document.getElementById('full_question_text');
    const markdownPreview = document.getElementById('markdown-preview');
    const resultModal = new bootstrap.Modal(document.getElementById('resultModal'));
    const aiCheckbox = document.getElementById('generate_ai_questions');
    const aiNotesSection = document.getElementById('ai_notes_section');

    // Explanation editor elements
    const explanationCheckbox = document.getElementById('add_explanation');
    const explanationEditor = document.getElementById('explanation-editor');
    const explanationInput = document.getElementById('explanation_text');
    const explanationPreview = document.getElementById('explanation-preview');

    // Initialize markdown preview
    updateMarkdownPreview();

    // Real-time markdown preview
    markdownInput.addEventListener('input', updateMarkdownPreview);

    // Form submission
    form.addEventListener('submit', handleFormSubmit);

    // Form reset
    form.addEventListener('reset', function () {
        setTimeout(() => {
            updateMarkdownPreview();
            updateExplanationPreview();
            form.classList.remove('was-validated');
            toggleAINotesSection();
            toggleExplanationEditor();
        }, 10);
    });

    // AI checkbox toggle
    aiCheckbox.addEventListener('change', toggleAINotesSection);

    // Explanation checkbox toggle
    explanationCheckbox.addEventListener('change', toggleExplanationEditor);

    // Explanation preview
    explanationInput.addEventListener('input', updateExplanationPreview);

    /**
     * Toggle explanation editor visibility
     */
    function toggleExplanationEditor() {
        if (explanationCheckbox.checked) {
            explanationEditor.style.display = 'block';
            explanationEditor.style.animation = 'fadeIn 0.3s ease-in';
        } else {
            explanationEditor.style.display = 'none';
        }
    }

    /**
     * Toggle AI notes section visibility
     */
    function toggleAINotesSection() {
        if (aiCheckbox.checked) {
            aiNotesSection.style.display = 'block';
            aiNotesSection.style.animation = 'fadeIn 0.3s ease-in';
        } else {
            aiNotesSection.style.display = 'none';
        }
    }

    /**
     * Update the explanation preview with markdown and LaTeX rendering
     */
    function updateExplanationPreview() {
        const explanationText = explanationInput.value.trim();

        if (!explanationText) {
            explanationPreview.innerHTML = '<em class="text-muted">Preview will appear here as you type...</em>';
            return;
        }

        // Render markdown
        const htmlContent = marked.parse(explanationText);
        explanationPreview.innerHTML = htmlContent;

        // Render LaTeX with MathJax
        if (window.MathJax) {
            MathJax.typesetPromise([explanationPreview]).catch((err) => {
                console.error('MathJax rendering error:', err);
            });
        }
    }


    /**
     * Update the markdown preview in real-time
     */
    function updateMarkdownPreview() {
        const markdownText = markdownInput.value.trim();

        if (markdownText === '') {
            markdownPreview.innerHTML = '<em class="text-muted">Preview will appear here as you type...</em>';
            return;
        }

        try {
            // Convert markdown to HTML using marked.js
            const htmlContent = marked.parse(markdownText);
            markdownPreview.innerHTML = htmlContent;

            // Render LaTeX with MathJax
            if (window.MathJax) {
                MathJax.typesetPromise([markdownPreview]).catch((err) => {
                    console.error('MathJax rendering error:', err);
                });
            }
        } catch (error) {
            markdownPreview.innerHTML = '<div class="alert alert-danger">Error rendering markdown: ' + error.message + '</div>';
        }
    }

    /**
     * Handle form submission
     */
    async function handleFormSubmit(event) {
        event.preventDefault();
        event.stopPropagation();

        // Add validation classes
        form.classList.add('was-validated');

        // Check if form is valid
        if (!form.checkValidity()) {
            return;
        }

        // Disable submit button and show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;

        if (aiCheckbox.checked) {
            submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Submitting & Generating AI Questions...';
        } else {
            submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Submitting...';
        }

        try {
            // Prepare form data
            const formData = new FormData(form);

            // Submit the form
            const response = await fetch('/submit', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.status === 'success') {
                let modalContent = `
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle"></i> ${result.message}
                    </div>
                    <h6>Original Question Details:</h6>
                    <div class="card mb-3">
                        <div class="card-body">
                            <p><strong>ID:</strong> ${result.data.id}</p>
                            <p><strong>Title:</strong> ${result.data.title}</p>
                            <p><strong>Subject:</strong> ${result.data.subject}</p>
                            <p><strong>Topic:</strong> ${result.data.topic}</p>
                            <p><strong>File Path:</strong> ${result.data.file_path}</p>
                        </div>
                    </div>
                `;

                // Add AI-generated questions info if any
                if (result.data.ai_generated_count > 0) {
                    modalContent += `
                        <h6>AI-Generated Questions:</h6>
                        <div class="alert alert-info">
                            <i class="bi bi-robot"></i> Successfully generated ${result.data.ai_generated_count} AI question variants!
                        </div>
                        <div class="row">
                    `;

                    result.data.ai_questions.forEach((aiQ, index) => {
                        modalContent += `
                            <div class="col-md-4 mb-2">
                                <div class="card">
                                    <div class="card-body">
                                        <h6 class="card-title">Variant ${index + 1}</h6>
                                        <p class="card-text"><small>ID: ${aiQ.id}</small></p>
                                        <p class="card-text"><small>File: ${aiQ.file_path}</small></p>
                                    </div>
                                </div>
                            </div>
                        `;
                    });

                    modalContent += '</div>';
                }

                showModal('Success!', modalContent, 'success');

                // Reset form on success
                form.reset();
                form.classList.remove('was-validated');
                updateMarkdownPreview();
                toggleAINotesSection();
            } else {
                showModal('Error!',
                    `<div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle"></i> ${result.message}
                    </div>`,
                    'error');
            }

        } catch (error) {
            showModal('Error!',
                `<div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Network error: ${error.message}
                </div>`,
                'error');
        } finally {
            // Re-enable submit button
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }

    /**
     * Show modal with result
     */
    function showModal(title, body, type) {
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');

        modalTitle.textContent = title;
        modalBody.innerHTML = body;

        // Add appropriate classes based on type
        const modalContent = document.querySelector('#resultModal .modal-content');
        modalContent.classList.remove('border-success', 'border-danger');

        if (type === 'success') {
            modalContent.classList.add('border-success');
        } else if (type === 'error') {
            modalContent.classList.add('border-danger');
        }

        resultModal.show();
    }

    /**
     * Add keyboard shortcuts for markdown formatting
     */
    markdownInput.addEventListener('keydown', function (event) {
        // Ctrl+B for bold
        if (event.ctrlKey && event.key === 'b') {
            event.preventDefault();
            insertMarkdownFormat('**', '**');
        }

        // Ctrl+I for italic
        if (event.ctrlKey && event.key === 'i') {
            event.preventDefault();
            insertMarkdownFormat('*', '*');
        }

        // Ctrl+K for code
        if (event.ctrlKey && event.key === 'k') {
            event.preventDefault();
            insertMarkdownFormat('`', '`');
        }
    });

    /**
     * Insert markdown formatting around selected text
     */
    function insertMarkdownFormat(before, after) {
        const start = markdownInput.selectionStart;
        const end = markdownInput.selectionEnd;
        const selectedText = markdownInput.value.substring(start, end);
        const replacement = before + selectedText + after;

        markdownInput.value = markdownInput.value.substring(0, start) + replacement + markdownInput.value.substring(end);

        // Set cursor position
        const newCursorPos = start + before.length + selectedText.length + after.length;
        markdownInput.setSelectionRange(newCursorPos, newCursorPos);

        // Update preview
        updateMarkdownPreview();

        // Focus back to textarea
        markdownInput.focus();
    }

    /**
     * Initialize tooltips
     */
    function initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Initialize tooltips if any exist
    initializeTooltips();

    // Add fade-in animation CSS
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    `;
    document.head.appendChild(style);

    // Initial check for correct answer field
    toggleCorrectAnswerField();
});

// Function to toggle correct answer field visibility
function toggleCorrectAnswerField() {
    const questionType = document.getElementById('question_type').value;
    const correctAnswerSection = document.getElementById('correct_answer_section');
    const rubricSection = document.getElementById('rubric_section');
    const correctAnswerInput = document.getElementById('correct_answer');
    const answerRubric = document.getElementById('answer_rubric');
    const answerLabel = document.getElementById('answer_label');
    const answerSmallText = document.getElementById('answer_help_text');

    if (!questionType) {
        correctAnswerSection.style.display = 'none';
        rubricSection.style.display = 'none';
        correctAnswerInput.required = false;
        answerRubric.required = false;
        return;
    }

    correctAnswerSection.style.display = 'block';
    correctAnswerSection.style.animation = 'fadeIn 0.3s ease-in';
    correctAnswerInput.required = true;

    // Simple types: MCQ, True/False, Fill-in-the-blank
    if (['MCQ', 'True/False', 'Fill-in-the-blank'].includes(questionType)) {
        rubricSection.style.display = 'none';
        answerRubric.required = false;
        answerRubric.value = ''; // Clear rubric

        answerLabel.textContent = "Correct Answer";

        if (questionType === 'MCQ') {
            correctAnswerInput.placeholder = "e.g., A, B, C, or D";
            answerSmallText.textContent = "Enter the option label (A, B, C, D) corresponding to the correct answer.";
        } else if (questionType === 'True/False') {
            correctAnswerInput.placeholder = "e.g., True or False";
            answerSmallText.textContent = "Enter 'True' or 'False'.";
        } else {
            correctAnswerInput.placeholder = "e.g., Photosynthesis";
            answerSmallText.textContent = "Enter the exact word or phrase expected as the answer.";
        }
    }
    // Complex types: Numerical, Coding, Short Answer, Descriptive
    else {
        rubricSection.style.display = 'block';
        rubricSection.style.animation = 'fadeIn 0.3s ease-in';
        answerRubric.required = true;

        answerLabel.textContent = "Formal Answer";
        
        correctAnswerInput.placeholder = "Enter the formal correct answer...";
        answerSmallText.textContent = "The formal valid answer to present.";

        if (questionType === 'Coding') {
            answerRubric.placeholder = "Enter the expected code solution or algorithm steps...";
        } else if (questionType === 'Numerical') {
            answerRubric.placeholder = "Enter the evaluation steps... (e.g. 1 mark for formula...)";
        } else {
            answerRubric.placeholder = "Enter the detailed answer key or evaluation rubric...";
        }
    }
}

// AI Question Feedback Modal Component
// This should be included in student question-solving pages

class AIQuestionFeedbackModal {
    constructor() {
        this.modalHTML = `
            <div class="modal fade" id="aiFeedbackModal" tabindex="-1" aria-labelledby="feedbackModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="feedbackModalLabel">
                                <i class="bi bi-chat-left-text"></i> Question Feedback
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <p class="text-muted">This is an AI-generated question. Your feedback helps improve question quality.</p>
                            
                            <form id="feedbackForm">
                                <input type="hidden" id="questionIdInput" name="question_id">
                                
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Is the question clear and understandable?</label>
                                    <div class="form-check">
                                        <input class="form-check-input" type="radio" name="is_question_clear" id="clearYes" value="true" required>
                                        <label class="form-check-label" for="clearYes">Yes</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="radio" name="is_question_clear" id="clearNo" value="false">
                                        <label class="form-check-label" for="clearNo">No</label>
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Does the provided answer seem correct?</label>
                                    <div class="form-check">
                                        <input class="form-check-input" type="radio" name="is_answer_correct" id="answerYes" value="true" required>
                                        <label class="form-check-label" for="answerYes">Yes</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="radio" name="is_answer_correct" id="answerNo" value="false">
                                        <label class="form-check-label" for="answerNo">No</label>
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Is the difficulty level appropriate?</label>
                                    <div class="form-check">
                                        <input class="form-check-input" type="radio" name="is_difficulty_appropriate" id="difficultyYes" value="true" required>
                                        <label class="form-check-label" for="difficultyYes">Yes</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="radio" name="is_difficulty_appropriate" id="difficultyNo" value="false">
                                        <label class="form-check-label" for="difficultyNo">No</label>
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="additionalComments" class="form-label">Additional Comments (Optional)</label>
                                    <textarea class="form-control" id="additionalComments" name="additional_comments" rows="3" 
                                              placeholder="Any additional feedback..."></textarea>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Skip Feedback</button>
                            <button type="button" class="btn btn-primary" onclick="aiQuestionFeedback.submitFeedback()">
                                <i class="bi bi-send"></i> Submit Feedback
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.currentQuestionId = null;
        this.modal = null;
        this.init();
    }

    init() {
        // Inject modal HTML into page
        if (!document.getElementById('aiFeedbackModal')) {
            document.body.insertAdjacentHTML('beforeend', this.modalHTML);
            this.modal = new bootstrap.Modal(document.getElementById('aiFeedbackModal'));
        }
    }

    async checkAndShowFeedback(questionId) {
        try {
            const response = await fetch(`/api/check_feedback_needed/${questionId}`);
            const data = await response.json();

            if (data.needs_feedback) {
                this.currentQuestionId = questionId;
                this.showModal();
            }
        } catch (error) {
            console.error('Error checking feedback need:', error);
        }
    }

    showModal() {
        document.getElementById('questionIdInput').value = this.currentQuestionId;
        document.getElementById('feedbackForm').reset();
        this.modal.show();
    }

    async submitFeedback() {
        const form = document.getElementById('feedbackForm');

        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const formData = new FormData(form);
        const feedbackData = {
            question_id: parseInt(formData.get('question_id')),
            is_question_clear: formData.get('is_question_clear') === 'true',
            is_answer_correct: formData.get('is_answer_correct') === 'true',
            is_difficulty_appropriate: formData.get('is_difficulty_appropriate') === 'true',
            additional_comments: formData.get('additional_comments') || ''
        };

        try {
            const response = await fetch('/api/submit_feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(feedbackData)
            });

            const data = await response.json();

            if (data.success) {
                this.modal.hide();
                this.showSuccessMessage(data.message, data.auto_accepted);
            } else {
                alert('Error: ' + (data.error || 'Failed to submit feedback'));
            }
        } catch (error) {
            alert('Error submitting feedback: ' + error.message);
        }
    }

    showSuccessMessage(message, autoAccepted) {
        const alertClass = autoAccepted ? 'alert-success' : 'alert-info';
        const alertHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                <strong>Thank you!</strong> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;

        // Find a container to show the alert (customize based on your page structure)
        const container = document.querySelector('.container, .container-fluid');
        if (container) {
            container.insertAdjacentHTML('afterbegin', alertHTML);

            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                const alert = container.querySelector('.alert');
                if (alert) {
                    alert.remove();
                }
            }, 5000);
        }
    }
}

// Initialize the feedback modal
const aiQuestionFeedback = new AIQuestionFeedbackModal();

// Example usage:
// After student submits an answer, call:
// aiQuestionFeedback.checkAndShowFeedback(questionId);

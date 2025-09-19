// Starry background animation (reused from dashboard)
const canvas = document.getElementById("stars");
const ctx = canvas.getContext("2d");

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
resizeCanvas();
window.addEventListener("resize", resizeCanvas);

let stars = [];
for (let i = 0; i < 150; i++) {
    stars.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        radius: Math.random() * 1.5,
        speed: Math.random() * 0.5 + 0.2,
        opacity: Math.random() * 0.8 + 0.2
    });
}

function animateStars() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    stars.forEach(star => {
        ctx.globalAlpha = star.opacity;
        ctx.fillStyle = "#fff";
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
        ctx.fill();

        star.y += star.speed;
        if (star.y > canvas.height) {
            star.y = 0;
            star.x = Math.random() * canvas.width;
        }
    });

    requestAnimationFrame(animateStars);
}
animateStars();

// Quiz functionality
class CosmicQuiz {
    constructor() {
        this.questions = [];
        this.currentQuestion = 0;
        this.answers = [];
        this.init();
    }

    async init() {
        await this.loadQuestions();
        this.setupEventListeners();
    }

    async loadQuestions() {
        try {
            const response = await fetch('/api/questions');
            this.questions = await response.json();
        } catch (error) {
            console.error('Error loading questions:', error);
            this.showError('Failed to load quiz questions. Please refresh the page.');
        }
    }

    setupEventListeners() {
        document.getElementById('startQuiz').addEventListener('click', () => this.startQuiz());
        document.getElementById('nextBtn').addEventListener('click', () => this.nextQuestion());
        document.getElementById('prevBtn').addEventListener('click', () => this.prevQuestion());
        document.getElementById('retakeQuiz').addEventListener('click', () => this.resetQuiz());
        document.getElementById('shareResult').addEventListener('click', () => this.shareResult());
    }

    startQuiz() {
        this.showScreen('quizScreen');
        this.displayQuestion();
    }

    displayQuestion() {
        if (this.currentQuestion >= this.questions.length) {
            this.showResults();
            return;
        }

        const question = this.questions[this.currentQuestion];
        document.getElementById('questionText').textContent = question.q;
        document.getElementById('questionCounter').textContent = `${this.currentQuestion + 1} / ${this.questions.length}`;

        // Update progress bar
        const progress = ((this.currentQuestion + 1) / this.questions.length) * 100;
        document.getElementById('progressFill').style.width = `${progress}%`;

        // Display options
        const optionsContainer = document.getElementById('optionsContainer');
        optionsContainer.innerHTML = '';

        question.opts.forEach((option, index) => {
            const optionElement = document.createElement('div');
            optionElement.className = 'option';
            optionElement.innerHTML = `
                <input type="radio" id="option${index}" name="question${this.currentQuestion}" value="${option}">
                <label for="option${index}" class="option-label">
                    <span class="option-text">${option}</span>
                    <span class="option-check">✨</span>
                </label>
            `;
            optionsContainer.appendChild(optionElement);

            // Add click event to the entire option
            optionElement.addEventListener('click', () => {
                const radio = optionElement.querySelector('input[type="radio"]');
                radio.checked = true;
                this.selectOption(option);
            });
        });

        // Update navigation buttons
        document.getElementById('prevBtn').disabled = this.currentQuestion === 0;
        document.getElementById('nextBtn').disabled = true;

        // If there's a previous answer, select it
        if (this.answers[this.currentQuestion]) {
            const savedAnswer = this.answers[this.currentQuestion];
            const radioButton = document.querySelector(`input[value="${savedAnswer}"]`);
            if (radioButton) {
                radioButton.checked = true;
                document.getElementById('nextBtn').disabled = false;
            }
        }
    }

    selectOption(answer) {
        this.answers[this.currentQuestion] = answer;
        document.getElementById('nextBtn').disabled = false;

        // Add visual feedback
        document.querySelectorAll('.option').forEach(opt => opt.classList.remove('selected'));
        event.currentTarget.classList.add('selected');
    }

    nextQuestion() {
        if (this.currentQuestion < this.questions.length - 1) {
            this.currentQuestion++;
            this.displayQuestion();
        } else {
            this.showResults();
        }
    }

    prevQuestion() {
        if (this.currentQuestion > 0) {
            this.currentQuestion--;
            this.displayQuestion();
        }
    }

    async showResults() {
        this.showScreen('resultsScreen');
        document.getElementById('loadingAnimation').style.display = 'block';
        document.getElementById('resultsContent').style.display = 'none';

        try {
            const response = await fetch('/api/gemini', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    answers: this.answers
                })
            });

            const result = await response.json();

            // Simulate loading time for better UX
            setTimeout(() => {
                document.getElementById('loadingAnimation').style.display = 'none';
                document.getElementById('resultsContent').style.display = 'block';
                document.getElementById('flowerResult').innerHTML = result.text;
                this.animateResults();
            }, 2000);

        } catch (error) {
            console.error('Error getting results:', error);
            document.getElementById('loadingAnimation').style.display = 'none';
            document.getElementById('resultsContent').style.display = 'block';
            document.getElementById('flowerResult').innerHTML = '<p>Unable to determine your cosmic flower. Please try again.</p>';
        }
    }

    animateResults() {
        const resultContent = document.getElementById('resultsContent');
        resultContent.style.opacity = '0';
        resultContent.style.transform = 'translateY(20px)';

        setTimeout(() => {
            resultContent.style.transition = 'all 0.8s ease';
            resultContent.style.opacity = '1';
            resultContent.style.transform = 'translateY(0)';
        }, 100);
    }

    shareResult() {
        const flowerResult = document.getElementById('flowerResult').textContent;
        if (navigator.share) {
            navigator.share({
                title: 'My Cosmic Flower Result',
                text: `I just discovered my cosmic flower personality: ${flowerResult}`,
                url: window.location.href
            });
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(`I just discovered my cosmic flower personality: ${flowerResult} - Take the quiz at ${window.location.href}`);
            this.showNotification('Result copied to clipboard! 🌸', 'success');
        }
    }

    resetQuiz() {
        this.currentQuestion = 0;
        this.answers = [];
        this.showScreen('startScreen');
    }

    showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        document.getElementById(screenId).classList.add('active');
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <p>${message}</p>
        `;
        document.querySelector('.container').appendChild(errorDiv);
    }

    showNotification(message, type = 'info') {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.notification');
        existingNotifications.forEach(notif => notif.remove());

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
                <span>${message}</span>
            </div>
        `;

        // Add notification styles
        notification.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: ${type === 'success' ? 'rgba(76, 175, 80, 0.9)' : type === 'error' ? 'rgba(244, 67, 54, 0.9)' : 'rgba(33, 150, 243, 0.9)'};
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            z-index: 1000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        `;

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Auto remove after 4 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }
}

// Initialize quiz when page loads
document.addEventListener('DOMContentLoaded', () => {
    new CosmicQuiz();
});

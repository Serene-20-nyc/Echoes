// Starry background animation
const canvas = document.getElementById("stars");
if (!canvas) {
    console.log("No stars canvas found, skipping animation");
} else {
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

// Secret form handling
const secretForm = document.getElementById('secretForm');
if (secretForm) {
    secretForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const title = document.getElementById('title').value;
    const content = document.getElementById('content').value;
    const isAnonymous = document.getElementById('anonymous').checked;
    
    console.log('🔍 Form data:', { title, content, isAnonymous });
    
    if (!title.trim() || !content.trim()) {
        showNotification('Please fill in both title and content', 'error');
        return;
    }
    
    const payload = {
        title: title.trim(),
        content: content.trim(),
        is_anonymous: isAnonymous
    };
    
    console.log('📤 Sending payload:', payload);
    
    try {
        const response = await fetch('/api/secrets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        console.log('📥 Response status:', response.status);
        
        const result = await response.json();
        console.log('📥 Response data:', result);
        
        if (response.ok) {
            showNotification('Secret shared successfully! ✨', 'success');
            document.getElementById('secretForm').reset();
            loadSecrets(); // Refresh the feed
        } else {
            showNotification(result.message || 'Failed to share secret', 'error');
            console.error('❌ Server error:', result);
        }
    } catch (error) {
        showNotification('Network error. Please try again.', 'error');
        console.error('❌ Network error:', error);
    }
    });
}

// Load and display secrets
async function loadSecrets() {
    const feedContainer = document.getElementById('secretsFeed');
    feedContainer.innerHTML = '<div class="loading">Loading whispers from the cosmos</div>';
    
    try {
        const response = await fetch('/api/secrets');
        const secrets = await response.json();
        
        if (secrets.length === 0) {
            feedContainer.innerHTML = `
                <div class="no-secrets">
                    <i class="fas fa-heart" style="font-size: 3rem; color: #ffb6c1; margin-bottom: 20px;"></i>
                    <p>No secrets shared yet. Be the first to whisper into the cosmos!</p>
                </div>
            `;
            return;
        }
        
        feedContainer.innerHTML = secrets.map(secret => createSecretCard(secret)).join('');
        
        // Add staggered animation to cards
        const cards = feedContainer.querySelectorAll('.secret-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            setTimeout(() => {
                card.style.transition = 'all 0.5s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        });
        
    } catch (error) {
        feedContainer.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle" style="color: #ff6b6b;"></i>
                <p>Failed to load secrets. Please refresh the page.</p>
            </div>
        `;
        console.error('Error loading secrets:', error);
    }
}

// Create secret card HTML
function createSecretCard(secret) {
    const date = new Date(secret.created_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    return `
        <div class="secret-card">
            <div class="secret-header">
                <h3 class="secret-title">${escapeHtml(secret.title)}</h3>
                <div class="secret-meta">
                    <span class="secret-author">
                        <i class="fas fa-user"></i> ${escapeHtml(secret.author)}
                    </span>
                </div>
            </div>
            <div class="secret-content">${escapeHtml(secret.content)}</div>
            <div class="secret-date">
                <i class="fas fa-clock"></i> ${date}
            </div>
        </div>
    `;
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Notification system
function showNotification(message, type = 'info') {
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

// Auto-resize textarea
const contentTextarea = document.getElementById('content');
if (contentTextarea) {
    contentTextarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 200) + 'px';
    });
}

// Load secrets when page loads
document.addEventListener('DOMContentLoaded', loadSecrets);

// Refresh secrets every 30 seconds
setInterval(loadSecrets, 30000);

} // Close the canvas check if statement

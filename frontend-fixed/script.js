// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');

    setupEventListeners();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });


    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    sendButton.disabled = true;

    // Add user message to chat
    addMessage('user', query);

    try {
        // Show loading indicator
        const loadingId = addMessage('assistant', '...');

        // Make API request
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Remove loading message
        removeMessage(loadingId);

        // Add assistant response
        addMessage('assistant', data.answer);

        // Update session ID
        currentSessionId = data.session_id;

    } catch (error) {
        console.error('Error:', error);
        removeMessage(loadingId);
        addMessage('assistant', `Error: ${error.message}`);
    } finally {
        sendButton.disabled = false;
        chatInput.focus();
    }
}

// Helper Functions
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    if (role === 'user') {
        contentDiv.textContent = content;
    } else {
        contentDiv.innerHTML = marked.parse(content);
    }

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageDiv;
}

function removeMessage(element) {
    if (element && element.parentNode) {
        element.parentNode.removeChild(element);
    }
}

function createNewSession() {
    currentSessionId = `session_${Date.now()}`;
}

async function loadCourseStats() {
    try {
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const data = await response.json();

        totalCourses.textContent = data.total_courses;

        if (data.course_titles && data.course_titles.length > 0) {
            courseTitles.innerHTML = data.course_titles
                .map(title => `<span class="course-title">${title}</span>`)
                .join('');
        }
    } catch (error) {
        console.error('Error loading course stats:', error);
        courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
    }
}
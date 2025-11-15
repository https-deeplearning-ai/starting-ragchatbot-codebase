// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, newChatButton;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    newChatButton = document.getElementById('newChatButton');
    
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

    // New chat button
    newChatButton.addEventListener('click', () => {
        createNewSession();
        chatInput.focus();
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
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
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

        // Handle HTTP errors with detailed messages
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorDetail = errorData.detail || 'Query failed to process';
            throw new Error(errorDetail);
        }

        const data = await response.json();

        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Replace loading message with helpful error message
        loadingMessage.remove();

        console.error('Query error details:', error);

        // Provide user-friendly error messages based on error type
        let errorMessage = 'Failed to process your query.';
        const errorStr = error.message.toLowerCase();

        if (errorStr.includes('network') || errorStr.includes('fetch')) {
            errorMessage = 'Network error. Please check your internet connection and try again.';
        } else if (errorStr.includes('timeout') || errorStr.includes('timed out')) {
            errorMessage = 'Request timed out. Please try again.';
        } else if (errorStr.includes('rate limit')) {
            errorMessage = 'Too many requests. Please wait a moment before trying again.';
        } else if (errorStr.includes('api key') || errorStr.includes('authentication')) {
            errorMessage = 'Authentication error. Please contact support.';
        } else if (errorStr.includes('connect') || errorStr.includes('connection')) {
            errorMessage = 'Connection error. Please try again in a moment.';
        } else if (error.message && error.message !== 'Query failed') {
            // Use the actual error message if it's informative
            errorMessage = error.message;
        }

        addMessage(`⚠️ ${errorMessage}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;
    
    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        // Format sources as clickable links in a list
        const sourceLinks = sources.map((source, index) => {
            let linkHtml;
            // Handle both old format (string) and new format (object with text and url)
            if (typeof source === 'string') {
                // Legacy format - display as plain text
                linkHtml = escapeHtml(source);
            } else if (source.url) {
                // New format with URL - create clickable link with icon
                linkHtml = `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer" class="source-link">
                    <span class="source-icon">📚</span>
                    ${escapeHtml(source.text)}
                    <span class="external-icon">↗</span>
                </a>`;
            } else {
                // New format but no URL - display as plain text
                linkHtml = `<span class="source-icon">📚</span>${escapeHtml(source.text)}`;
            }
            return `<div class="source-item">${linkHtml}</div>`;
        }).join('');

        html += `
            <details class="sources-collapsible" open>
                <summary class="sources-header">📖 Sources (${sources.length})</summary>
                <div class="sources-content">${sourceLinks}</div>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');
        
        const data = await response.json();
        console.log('Course data received:', data);
        
        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }
        
        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}
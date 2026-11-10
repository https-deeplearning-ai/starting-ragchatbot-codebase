// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;
// Bumped on every new chat so responses to requests from an old chat are dropped
let chatGeneration = 0;

// DOM elements
let chatMessages, chatInput, sendButton, newChatButton, totalCourses, courseTitles, themeToggle;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    newChatButton = document.getElementById('newChatButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    themeToggle = document.getElementById('themeToggle');

    updateThemeToggle(getCurrentTheme());
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

    // New chat
    newChatButton.addEventListener('click', startNewChat);

    // Theme toggle (a native <button>, so Enter/Space work out of the box)
    themeToggle.addEventListener('click', toggleTheme);

    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Theme Functions
let themeTransitionTimer = null;

function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
}

function updateThemeToggle(theme) {
    const label = theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme';
    themeToggle.setAttribute('aria-label', label);
    themeToggle.setAttribute('title', label);
}

function toggleTheme() {
    const next = getCurrentTheme() === 'light' ? 'dark' : 'light';
    const root = document.documentElement;

    // Crossfade colors only while switching (skipped for reduced-motion users)
    const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reduceMotion) {
        root.classList.add('theme-transition');
        clearTimeout(themeTransitionTimer);
        themeTransitionTimer = setTimeout(() => root.classList.remove('theme-transition'), 350);
    }

    root.setAttribute('data-theme', next);
    updateThemeToggle(next);
    try {
        localStorage.setItem('theme', next);
    } catch (e) {
        // Storage unavailable (e.g. private mode): theme still applies for this page
    }
}

// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;
    const generation = chatGeneration;

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

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();

        // User started a new chat while this was in flight: discard the answer
        // and the session the server may have created for it.
        if (generation !== chatGeneration) {
            if (data.session_id && data.session_id !== currentSessionId) {
                deleteServerSession(data.session_id);
            }
            return;
        }

        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        if (generation !== chatGeneration) return;
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        if (generation !== chatGeneration) return;
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
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <ul class="sources-list">${sources.map(s => `<li>${renderSource(s)}</li>`).join('')}</ul>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Render one source: a link to the lesson video when a safe http(s) URL is known,
// otherwise plain text. Only the label is visible; the URL stays in the href.
function renderSource(source) {
    const label = escapeHtml(source.label);
    const url = source.url;
    if (url && /^https?:\/\//i.test(url)) {
        const href = escapeHtml(url).replace(/"/g, '&quot;');
        return `<a class="source-link" href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`;
    }
    return `<span>${label}</span>`;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

// Start a fresh conversation without reloading: drop the old session on the
// server, ignore any in-flight answer, and reset the chat UI.
function startNewChat() {
    if (currentSessionId) deleteServerSession(currentSessionId);
    chatGeneration++;
    createNewSession();
    chatInput.value = '';
    chatInput.disabled = false;
    sendButton.disabled = false;
    chatInput.focus();
}

// Best-effort cleanup; a failure only leaves an orphaned in-memory session.
function deleteServerSession(sessionId) {
    fetch(`${API_URL}/session/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
        .catch(err => console.warn('Failed to delete session', sessionId, err));
}

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
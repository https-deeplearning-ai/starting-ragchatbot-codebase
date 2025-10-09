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
    newChatButton.addEventListener('click', clearCurrentChat);

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

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();
        
        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
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
        // Convert sources to clickable links
        const sourceLinks = sources.map(source => {
            // Handle both string and object sources for backward compatibility
            if (typeof source === 'string') {
                return escapeHtml(source);
            } else if (source && typeof source === 'object' && source.text) {
                // If source has a link, create clickable link that opens in new tab
                if (source.link) {
                    return `<a href="${escapeHtml(source.link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.text)}</a>`;
                } else {
                    return escapeHtml(source.text);
                }
            }
            // Fallback for unexpected source types
            return escapeHtml(String(source));
        });

        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${sourceLinks.join('')}</div>
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

async function clearCurrentChat() {
    // Clear session on backend if one exists
    if (currentSessionId) {
        try {
            await fetch(`${API_URL}/clear_session`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: currentSessionId
                })
            });
        } catch (error) {
            console.error('Error clearing session:', error);
            // Continue with frontend reset even if backend fails
        }
    }

    // Reset frontend state
    createNewSession();
}

// Setup click handlers for course titles
function setupCourseClickHandlers() {
    // Add a small delay to ensure DOM is updated
    setTimeout(() => {
        const courseElements = document.querySelectorAll('.clickable-course');
        console.log('Setting up click handlers for', courseElements.length, 'course elements');

        courseElements.forEach(courseElement => {
            courseElement.addEventListener('click', (e) => {
                const courseTitle = e.target.getAttribute('data-course-title');
                console.log('Course clicked:', courseTitle);
                if (courseTitle) {
                    // Use the fast course outline endpoint instead of chat
                    getCourseOutlineFast(courseTitle);
                }
            });
        });
    }, 100);
}

// Fast course outline retrieval
async function getCourseOutlineFast(courseTitle) {
    // Clear previous chat contents for course outline requests
    chatMessages.innerHTML = '';

    // Add user message showing what was clicked
    addMessage(`Show outline for "${courseTitle}"`, 'user');

    // Add loading message
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/course_outline`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                course_title: courseTitle
            })
        });

        if (!response.ok) {
            throw new Error(`Course outline request failed: ${response.status}`);
        }

        const data = await response.json();

        // Replace loading message with the formatted outline
        loadingMessage.remove();
        addMessage(data.formatted_outline, 'assistant');

    } catch (error) {
        console.error('Fast outline error:', error);
        // Replace loading message with error, fallback to regular chat
        loadingMessage.remove();
        addMessage(`Error loading outline. Trying alternative method...`, 'assistant');

        // Fallback to regular chat query
        chatInput.value = `What is the outline of the "${courseTitle}" course?`;
        sendMessage();
    }
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
        
        // Update course titles with clickable links
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item clickable-course" data-course-title="${escapeHtml(title)}">${escapeHtml(title)}</div>`)
                    .join('');

                // Add click handlers to course titles
                setupCourseClickHandlers();
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
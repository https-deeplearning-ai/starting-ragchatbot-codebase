// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;
let currentLanguage = 'en';

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, newChatButton;
let languageToggle, languageMenu, languageOptions;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    newChatButton = document.getElementById('newChatButton');
    languageToggle = document.getElementById('languageToggle');
    languageMenu = document.getElementById('languageMenu');
    languageOptions = document.querySelectorAll('.language-option');

    // Initialize language
    currentLanguage = getCurrentLanguage();
    updateLanguageUI();

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
    if (newChatButton) {
        newChatButton.addEventListener('click', newChat);
    }

    // Language selector
    if (languageToggle) {
        languageToggle.addEventListener('click', toggleLanguageMenu);
    }

    if (languageOptions) {
        languageOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                const lang = e.target.getAttribute('data-lang');
                changeLanguage(lang);
            });
        });
    }

    // Close language menu when clicking outside
    document.addEventListener('click', (e) => {
        if (languageMenu && languageToggle && !languageToggle.contains(e.target) && !languageMenu.contains(e.target)) {
            languageMenu.style.display = 'none';
        }
    });

    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach((button, index) => {
        button.addEventListener('click', (e) => {
            // Get the question based on current language
            const questionKey = `suggestedQuestion${index + 1}`;
            const question = t(questionKey);
            chatInput.value = question;
            sendMessage();
        });
    });
}


    document.getElementById('uploadBtn').addEventListener('click', async () => {
        const fileInput = document.getElementById('courseFile');
        const file = fileInput.files[0];
        if (!file) {
            document.getElementById('uploadStatus').textContent = 'Please select a file';
            document.getElementById('uploadStatus').style.display = 'block';
            return;
        }
        if (!file.name.endsWith('.txt')) {
            document.getElementById('uploadStatus').textContent = 'Only .txt files are allowed';
            document.getElementById('uploadStatus').style.display = 'block';
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload-course', {
                method: 'POST',
                body: formData
            });
            if (response.ok) {
                loadCourseStats();
                fileInput.value = '';
                document.getElementById('uploadStatus').textContent = 'Upload successful!';
                document.getElementById('uploadStatus').style.display = 'block';
                setTimeout(() => {
                    document.getElementById('uploadStatus').style.display = 'none';
                }, 3000);
            } else {
                const error = await response.json();
                document.getElementById('uploadStatus').textContent = `Error: ${error.detail}`;
                document.getElementById('uploadStatus').style.display = 'block';
            }
        } catch (error) {
            document.getElementById('uploadStatus').textContent = `Network error: ${error.message}`;
            document.getElementById('uploadStatus').style.display = 'block';
        }
    });

// Language Functions
function toggleLanguageMenu() {
    if (languageMenu.style.display === 'none') {
        languageMenu.style.display = 'block';
    } else {
        languageMenu.style.display = 'none';
    }
}

function changeLanguage(lang) {
    if (setLanguage(lang)) {
        currentLanguage = lang;
        languageMenu.style.display = 'none';
        updateLanguageUI();
    }
}

function updateLanguageUI() {
    // Update language toggle button
    const langText = currentLanguage === 'en' ? 'EN' : '中文';
    const langToggleText = languageToggle.querySelector('.language-text');
    if (langToggleText) {
        langToggleText.textContent = langText;
    }

    // Update active language option
    languageOptions.forEach(option => {
        if (option.getAttribute('data-lang') === currentLanguage) {
            option.classList.add('active');
        } else {
            option.classList.remove('active');
        }
    });

    // Update all UI text
    updatePageText();
}

function updatePageText() {
    // Update sidebar
    if (newChatButton) {
        newChatButton.textContent = t('newChat');
    }

    // Update course stats header
    const statsHeader = document.querySelector('.stats-header');
    if (statsHeader) {
        statsHeader.textContent = t('courses');
    }

    // Update course stats label
    const statLabel = document.querySelector('.stat-label');
    if (statLabel) {
        statLabel.textContent = t('numberOfCourses');
    }

    // Update suggested questions header
    const suggestedHeader = document.querySelector('.suggested-header');
    if (suggestedHeader) {
        suggestedHeader.textContent = t('tryAsking');
    }

    // Update chat input placeholder
    if (chatInput) {
        chatInput.placeholder = t('placeholder');
    }

    // Update suggested questions text
    const suggestedItems = document.querySelectorAll('.suggested-item');
    const suggestedTexts = [
        t('outlineOfCourse'),
        t('courseAboutChatbot'),
        t('courseExplainingRAG'),
        t('detailsOfLesson')
    ];
    suggestedItems.forEach((item, index) => {
        if (index < suggestedTexts.length) {
            item.textContent = suggestedTexts[index];
        }
    });

    // Update sources header in existing messages
    document.querySelectorAll('.sources-header').forEach(header => {
        header.textContent = t('sources');
    });
}

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
                session_id: currentSessionId,
                language: currentLanguage  // Send current language preference
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
    let displayContent;
    if (type === 'assistant') {
        try {
            if (typeof marked !== 'undefined') {
                displayContent = marked.parse(content);
            } else {
                console.warn('marked library not loaded, using plain text');
                displayContent = escapeHtml(content);
            }
        } catch (e) {
            console.error('Markdown parsing error:', e);
            displayContent = escapeHtml(content);
        }
    } else {
        displayContent = escapeHtml(content);
    }
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">${t('sources')}</summary>
                <div class="sources-content">${sources.join(', ')}</div>
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
    addMessage(t('welcome'), 'assistant', null, true);
}

async function newChat() {
    // Clear current session on backend if exists
    if (currentSessionId) {
        try {
            await fetch(`${API_URL}/session/clear`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: currentSessionId
                })
            });
        } catch (error) {
            console.error('Failed to clear session on backend:', error);
            // Continue anyway
        }
    }
    // Create new session (clears chat window)
    createNewSession();
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
                courseTitles.innerHTML = `<span class="no-courses">${t('noCourses')}</span>`;
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = `<span class="error">${t('failedToLoadCourses')}</span>`;
        }
    }
}
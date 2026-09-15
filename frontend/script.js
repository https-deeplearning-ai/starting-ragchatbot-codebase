// API base URL - use relative path to work from any host
const API_URL = "/api";

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, newChatButton, themeToggle;

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  // Get DOM elements after page loads
  chatMessages = document.getElementById("chatMessages");
  chatInput = document.getElementById("chatInput");
  sendButton = document.getElementById("sendButton");
  totalCourses = document.getElementById("totalCourses");
  courseTitles = document.getElementById("courseTitles");
  newChatButton = document.getElementById("newChatButton");
  themeToggle = document.getElementById("themeToggle");

  initTheme();
  setupEventListeners();
  createNewSession();
  loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
  // Chat functionality
  sendButton.addEventListener("click", sendMessage);
  chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });

  // New chat
  newChatButton.addEventListener("click", createNewSession);

  // Theme toggle (native <button> handles Enter/Space for keyboard users)
  themeToggle.addEventListener("click", toggleTheme);

  // Suggested questions
  document.querySelectorAll(".suggested-item").forEach((button) => {
    button.addEventListener("click", (e) => {
      const question = e.target.getAttribute("data-question");
      chatInput.value = question;
      sendMessage();
    });
  });
}

// Theme Functions
// The theme itself is applied by an inline script in index.html (before first paint);
// these functions keep the toggle button's state in sync and handle switching.
function initTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  applyTheme(current, false);

  // Follow the OS setting as long as the user hasn't made an explicit choice
  const systemPrefersLight = window.matchMedia("(prefers-color-scheme: light)");
  systemPrefersLight.addEventListener("change", (e) => {
    if (!getStoredTheme()) {
      applyTheme(e.matches ? "light" : "dark", false);
    }
  });
}

function toggleTheme() {
  const current =
    document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  applyTheme(current === "light" ? "dark" : "light", true);
}

function applyTheme(theme, persist) {
  document.documentElement.setAttribute("data-theme", theme);

  if (persist) {
    try {
      localStorage.setItem("theme", theme);
    } catch (error) {
      console.error("Could not save theme preference:", error);
    }
  }

  if (themeToggle) {
    const label = theme === "light" ? "Switch to dark theme" : "Switch to light theme";
    themeToggle.setAttribute("aria-checked", theme === "light" ? "true" : "false");
    themeToggle.setAttribute("aria-label", label);
    themeToggle.setAttribute("title", label);
  }
}

function getStoredTheme() {
  try {
    return localStorage.getItem("theme");
  } catch (error) {
    return null;
  }
}

// Chat Functions
async function sendMessage() {
  const query = chatInput.value.trim();
  if (!query) return;

  // Disable input
  chatInput.value = "";
  chatInput.disabled = true;
  sendButton.disabled = true;

  // Add user message
  addMessage(query, "user");

  // Add loading message - create a unique container for it
  const loadingMessage = createLoadingMessage();
  chatMessages.appendChild(loadingMessage);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const response = await fetch(`${API_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: query,
        session_id: currentSessionId,
      }),
    });

    if (!response.ok) throw new Error("Query failed");

    const data = await response.json();

    // Update session ID if new
    if (!currentSessionId) {
      currentSessionId = data.session_id;
    }

    // Replace loading message with response
    loadingMessage.remove();
    addMessage(data.answer, "assistant", data.sources);
  } catch (error) {
    // Replace loading message with error
    loadingMessage.remove();
    addMessage(`Error: ${error.message}`, "assistant");
  } finally {
    chatInput.disabled = false;
    sendButton.disabled = false;
    chatInput.focus();
  }
}

function createLoadingMessage() {
  const messageDiv = document.createElement("div");
  messageDiv.className = "message assistant";
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
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${type}${isWelcome ? " welcome-message" : ""}`;
  messageDiv.id = `message-${messageId}`;

  // Convert markdown to HTML for assistant messages
  const displayContent = type === "assistant" ? marked.parse(content) : escapeHtml(content);

  let html = `<div class="message-content">${displayContent}</div>`;

  if (sources && sources.length > 0) {
    const sourceHtml = sources
      .map((source) => {
        const safeText = escapeHtml(source.text);
        if (source.link) {
          return `<li><a href="${escapeHtml(source.link)}" target="_blank" rel="noopener noreferrer" class="source-link">${safeText}</a></li>`;
        }
        return `<li><span class="source-item">${safeText}</span></li>`;
      })
      .join("");

    html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <ol class="sources-content">${sourceHtml}</ol>
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
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
  const oldSessionId = currentSessionId;
  currentSessionId = null;
  chatMessages.innerHTML = "";
  addMessage(
    "Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?",
    "assistant",
    null,
    true
  );
  chatInput.focus();

  // End the previous session on the backend so its history is freed
  if (oldSessionId) {
    try {
      await fetch(`${API_URL}/session/${oldSessionId}`, { method: "DELETE" });
    } catch (error) {
      console.error("Error ending previous session:", error);
    }
  }
}

// Load course statistics
async function loadCourseStats() {
  try {
    console.log("Loading course stats...");
    const response = await fetch(`${API_URL}/courses`);
    if (!response.ok) throw new Error("Failed to load course stats");

    const data = await response.json();
    console.log("Course data received:", data);

    // Update stats in UI
    if (totalCourses) {
      totalCourses.textContent = data.total_courses;
    }

    // Update course titles
    if (courseTitles) {
      if (data.course_titles && data.course_titles.length > 0) {
        courseTitles.innerHTML = data.course_titles
          .map((title) => `<div class="course-title-item">${title}</div>`)
          .join("");
      } else {
        courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
      }
    }
  } catch (error) {
    console.error("Error loading course stats:", error);
    // Set default values on error
    if (totalCourses) {
      totalCourses.textContent = "0";
    }
    if (courseTitles) {
      courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
    }
  }
}

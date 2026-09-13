const BACKEND_URL = "http://127.0.0.1:8000";

const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const langSelect = document.getElementById("lang-select");
const alertBanner = document.getElementById("alert-banner");
const chatForm = document.getElementById("chat-form");

// ---------------------------------------------------------------------------
// Conversation history — maintained in-memory for this session only.
// Sent with every request so the backend can provide contextual answers.
// Max 10 messages (5 turns) kept to limit payload size.
// ---------------------------------------------------------------------------
const MAX_HISTORY = 10;
let chatHistory = [];

function _pushHistory(role, content, extras = {}) {
  chatHistory.push({ role, content, ...extras });
  if (chatHistory.length > MAX_HISTORY) {
    chatHistory = chatHistory.slice(chatHistory.length - MAX_HISTORY);
  }
}

// ---------------------------------------------------------------------------
// DOM helpers — NO UI changes, same markup as before
// ---------------------------------------------------------------------------
function addMessage(text, sender) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `msg ${sender}`;
  msgDiv.textContent = text;
  chatWindow.appendChild(msgDiv);
  chatWindow.scrollTop = chatWindow.scrollHeight;

  // Audio readout hook from voice.js
  if (sender === "bot" && window.speakAnswer) {
    window.speakAnswer(text);
  }

  return msgDiv;
}

// ---------------------------------------------------------------------------
// Main send function
// ---------------------------------------------------------------------------
async function sendMessage(text) {
  if (!text || !text.trim()) return;

  const userText = text.trim();
  addMessage(userText, "user");
  userInput.value = "";

  // Store user message in history before sending
  _pushHistory("user", userText);

  // Temporary loading bubble
  const loadingDiv = addMessage("Thinking...", "bot loading");

  try {
    const lang = langSelect.value;

    // POST with JSON body — includes conversation history for context
    const response = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: userText,
        lang: lang,
        history: chatHistory.slice(0, -1), // exclude the message we just added
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(`HTTP ${response.status}: ${errData.detail || response.statusText}`);
    }

    const data = await response.json();
    loadingDiv.remove();

    const botReply = data.answer_text || data.message || "I could not find weather details for that location.";
    addMessage(botReply, "bot");

    // Store assistant reply in history, with optional metadata for context resolution
    _pushHistory("assistant", botReply, {
      location: data.location?.city || (data._ctx?.location ?? null),
      weather_data: data.data || null,
      context: data._ctx || null,
    });

    // Integration Hook — Leaflet map pin (unchanged)
    if (data.location && typeof window.updateMap === "function") {
      window.updateMap(data.location);
    }

    // Alert Banner Hook (unchanged)
    if (data.alert) {
      alertBanner.textContent = `⚠️ Alert: ${data.alert}`;
      alertBanner.classList.remove("hidden");
    } else {
      alertBanner.classList.add("hidden");
    }

  } catch (err) {
    loadingDiv.remove();

    // Remove the failed user message from history so it doesn't pollute context
    if (chatHistory.length && chatHistory[chatHistory.length - 1].role === "user") {
      chatHistory.pop();
    }

    const errorMessage = err.message.includes("404")
      ? "I could not find that city. Please check the spelling and try again."
      : err.message.includes("HTTP 5")
        ? "The weather service returned an error. Please try again shortly."
        : "Could not connect to the server. Please check if the backend is running.";

    addMessage(errorMessage, "bot");
    console.error("Fetch error:", err);
  }
}

// ---------------------------------------------------------------------------
// Form event listeners — unchanged
// ---------------------------------------------------------------------------
chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(userInput.value);
});

sendBtn.addEventListener("click", (e) => {
  e.preventDefault();
  sendMessage(userInput.value);
});

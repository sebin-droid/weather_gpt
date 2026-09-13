// ============================================================
// chat.js — WeatherGPT chat interface
// Upstream changes preserved: conversation history (_pushHistory,
// chatHistory, POST with JSON body including history).
// UI changes: message structure (avatar + text span), typing
// animation for loading state, user-friendly error wording,
// alert banner uses #alert-text span, sendMessage exposed globally.
// ============================================================

const BACKEND_URL = "http://127.0.0.1:8000";

const chatWindow  = document.getElementById("chat-window");
const userInput   = document.getElementById("user-input");
const sendBtn     = document.getElementById("send-btn");
const langSelect  = document.getElementById("lang-select");
const alertBanner = document.getElementById("alert-banner");
const chatForm    = document.getElementById("chat-form");

// ---------------------------------------------------------------------------
// Conversation history (upstream logic - UNCHANGED)
// Maintained in-memory; sent with every request for contextual answers.
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
// Feather icon helper (UI)
// ---------------------------------------------------------------------------
function featherSvg(name, size) {
  if (typeof feather !== "undefined" && feather.icons[name]) {
    return feather.icons[name].toSvg({ width: size || 12, height: size || 12, "stroke-width": 2 });
  }
  return "";
}

// ---------------------------------------------------------------------------
// Render a chat message (UI change: avatar + text-span structure)
// Sender values "user", "bot", "bot loading" — UNCHANGED.
// ---------------------------------------------------------------------------
function addMessage(text, sender) {
  const msgDiv = document.createElement("div");
  msgDiv.className = "msg " + sender;

  // Bot messages get an avatar icon
  if (sender.indexOf("bot") !== -1) {
    const avatar = document.createElement("span");
    avatar.className = "msg-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.innerHTML = featherSvg("cloud-rain", 12);
    msgDiv.appendChild(avatar);
  }

  const textSpan = document.createElement("span");
  textSpan.className = "msg-text";

  if (sender === "bot loading") {
    // Typing animation instead of plain "Thinking..."
    textSpan.innerHTML =
      '<span class="typing-dots" aria-label="Loading">' +
      '<span></span><span></span><span></span>' +
      '</span>';
  } else {
    textSpan.textContent = text;
  }

  msgDiv.appendChild(textSpan);
  chatWindow.appendChild(msgDiv);
  chatWindow.scrollTop = chatWindow.scrollHeight;

  // Audio readout hook from voice.js (unchanged)
  if (sender === "bot" && window.speakAnswer) {
    window.speakAnswer(text);
  }

  return msgDiv;
}

// ---------------------------------------------------------------------------
// Main send function
// API call: POST with JSON body including history (upstream - UNCHANGED)
// ---------------------------------------------------------------------------
async function sendMessage(text) {
  if (!text || !text.trim()) return;

  const userText = text.trim();
  addMessage(userText, "user");
  userInput.value = "";

  // Store user message in history before sending (upstream - UNCHANGED)
  _pushHistory("user", userText);

  const loadingDiv = addMessage("", "bot loading");

  try {
    const lang = langSelect.value;

    // POST with JSON body — includes conversation history (upstream - UNCHANGED)
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

    // Store assistant reply in history with metadata (upstream - UNCHANGED)
    _pushHistory("assistant", botReply, {
      location:     data.location?.city || (data._ctx?.location ?? null),
      weather_data: data.data || null,
      context:      data._ctx || null,
    });

    // Map pin integration hook (unchanged)
    if (data.location && typeof window.updateMap === "function") {
      window.updateMap(data.location);
    }

    // Alert banner — UI: targets #alert-text span
    if (data.alert) {
      const alertTextEl = document.getElementById("alert-text");
      if (alertTextEl) {
        alertTextEl.textContent = data.alert;
      } else {
        alertBanner.textContent = data.alert;
      }
      alertBanner.classList.remove("hidden");
    } else {
      alertBanner.classList.add("hidden");
    }

  } catch (err) {
    loadingDiv.remove();

    // Remove failed user message from history (upstream - UNCHANGED)
    if (chatHistory.length && chatHistory[chatHistory.length - 1].role === "user") {
      chatHistory.pop();
    }

    // User-friendly error messages (UI-only)
    let errorMessage;
    if (err.message.includes("404")) {
      errorMessage = "I could not find that city. Please check the spelling and try again.";
    } else if (err.message.includes("HTTP 5")) {
      errorMessage = "The weather service is temporarily unavailable. Please try again in a moment.";
    } else if (err.message.includes("HTTP")) {
      errorMessage = "Something went wrong on the server. Please try again shortly.";
    } else {
      errorMessage = "Unable to reach the server. Please check your connection and try again.";
    }

    addMessage(errorMessage, "bot");
    console.error("Fetch error:", err);
  }
}

// Expose sendMessage globally so quick-action chips can call it
window.sendMessage = sendMessage;

// ---------------------------------------------------------------------------
// Form event listeners (unchanged)
// ---------------------------------------------------------------------------
chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(userInput.value);
});

sendBtn.addEventListener("click", (e) => {
  e.preventDefault();
  sendMessage(userInput.value);
});

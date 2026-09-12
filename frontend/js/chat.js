const BACKEND_URL = "http://127.0.0.1:8000";

const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const langSelect = document.getElementById("lang-select");
const alertBanner = document.getElementById("alert-banner");
const chatForm = document.getElementById("chat-form");

function addMessage(text, sender) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `msg ${sender}`;
  msgDiv.textContent = text;
  chatWindow.appendChild(msgDiv);
  chatWindow.scrollTop = chatWindow.scrollHeight;

  // Audio readout hook for Person 5's voice.js
  if (sender === "bot" && window.speakAnswer) {
    window.speakAnswer(text);
  }

  return msgDiv;
}

async function sendMessage(text) {
  if (!text || !text.trim()) return;

  const userText = text.trim();
  addMessage(userText, "user");
  userInput.value = "";

  // Temporary loading bubble
  const loadingDiv = addMessage("Thinking...", "bot loading");

  try {
    const lang = langSelect.value;
    const url = `${BACKEND_URL}/chat?question=${encodeURIComponent(userText)}&lang=${encodeURIComponent(lang)}`;
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }

    const data = await response.json();
    loadingDiv.remove();

    const botReply = data.answer_text || data.message || "I could not find weather details for that location.";
    addMessage(botReply, "bot");

    // Integration Hook for Person 4 (Leaflet map pin)
    if (data.location && typeof window.updateMap === "function") {
      window.updateMap(data.location);
    }

    // Alert Banner Hook (from backend threshold alerts)
    if (data.alert) {
      alertBanner.textContent = `⚠️ Alert: ${data.alert}`;
      alertBanner.classList.remove("hidden");
    } else {
      alertBanner.classList.add("hidden");
    }

  } catch (err) {
    loadingDiv.remove();
    addMessage("Could not connect to the server. Please check if the backend is running.", "bot");
    console.error("Fetch error:", err);
  }
}

// Form event listeners
chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(userInput.value);
});

sendBtn.addEventListener("click", (e) => {
  e.preventDefault();
  sendMessage(userInput.value);
});
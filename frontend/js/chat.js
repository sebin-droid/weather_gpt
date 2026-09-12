const BACKEND_URL = "http://127.0.0.1:8000";

const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const langSelect = document.getElementById("lang-select");
const alertBanner = document.getElementById("alert-banner");

function addMessage(text, sender) {
  const div = document.createElement("div");
  div.className = `msg ${sender}`;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendMessage(text) {
  addMessage(text, "user");
  userInput.value = "";

  try {
    const lang = langSelect.value;
    const url = `${BACKEND_URL}/chat?question=${encodeURIComponent(text)}&lang=${lang}`;
    const res = await fetch(url);
    const data = await res.json();

    addMessage(data.answer_text || data.message || "Sorry, I did not understand.", "bot");

    if (data.location && window.updateMap) {
      window.updateMap(data.location);
    }

    if (data.alert) {
      alertBanner.textContent = data.alert;
      alertBanner.classList.remove("hidden");
    } else {
      alertBanner.classList.add("hidden");
    }

  } catch (err) {
    addMessage("Could not reach the server. Is the backend running?", "bot");
    console.error(err);
  }
}

sendBtn.addEventListener("click", () => {
  const text = userInput.value.trim();
  if (text) sendMessage(text);
});

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendBtn.click();
});

const voiceControls = document.getElementById("voice-controls");

const micBtn = document.createElement("button");
micBtn.textContent = "🎤 Speak";
voiceControls.appendChild(micBtn);

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
  const recognition = new SpeechRecognition();
  recognition.lang = "en-IN";

  micBtn.addEventListener("click", () => {
    recognition.start();
    micBtn.textContent = "🎙️ Listening...";
  });

  recognition.onresult = (event) => {
    const text = event.results[0][0].transcript;
    document.getElementById("user-input").value = text;
    micBtn.textContent = "🎤 Speak";
    document.getElementById("send-btn").click();
  };

  recognition.onerror = () => {
    micBtn.textContent = "🎤 Speak";
  };
} else {
  micBtn.disabled = true;
  micBtn.textContent = "🎤 Not supported in this browser";
}

// Read the bot's last answer out loud
function speak(text) {
  const utterance = new SpeechSynthesisUtterance(text);
  window.speechSynthesis.speak(utterance);
}

// Expose it so chat.js can call it after getting an answer
window.speakAnswer = speak;

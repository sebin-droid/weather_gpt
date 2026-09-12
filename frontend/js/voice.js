const voiceControls = document.getElementById("voice-controls");
const micBtn = document.createElement("button");
micBtn.type = "button";
micBtn.textContent = "🎤 Whisper Voice";
voiceControls.appendChild(micBtn);

let mediaRecorder;
let audioChunks = [];

micBtn.addEventListener("click", async () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    micBtn.textContent = "⏳ Transcribing...";
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
      const formData = new FormData();
      formData.append("file", audioBlob, "recording.wav");

      try {
        const response = await fetch("http://127.0.0.1:8000/speech-to-text", {
          method: "POST",
          body: formData
        });
        const data = await response.json();
        
        if (data.transcript) {
          document.getElementById("user-input").value = data.transcript;
          document.getElementById("send-btn").click();
        }
      } catch (err) {
        console.error("Whisper Error:", err);
      }
      micBtn.textContent = "🎤 Record Voice";
    };

    mediaRecorder.start();
    micBtn.textContent = "🛑 Stop Recording";
  } catch (err) {
    alert("Microphone access denied or unavailable.");
  }
});

// Text-to-Speech function
window.speakAnswer = function(text) {
  if (!("speechSynthesis" in window)) {
    console.warn("Speech synthesis not supported in this browser.");
    return;
  }

  // Cancel any ongoing speech
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);

// Read the active language from the dropdown
  const langSelect = document.getElementById("lang-select");
  const currentLang = langSelect ? langSelect.value : "en";

  // Map language codes to BCP 47 voice tags
  const langMap = {
    en: "en-IN",
    hi: "hi-IN",
    ml: "ml-IN",
    ta: "ta-IN"
  };

  utterance.lang = langMap[currentLang] || "en-IN";
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  window.speechSynthesis.speak(utterance);
};
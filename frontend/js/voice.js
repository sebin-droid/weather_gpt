// ============================================================
// voice.js — Voice input (Whisper) + Text-to-Speech
// Recording logic, API call (/speech-to-text), audio handling:
// ALL UNCHANGED.
// UI changes: mic button text labels, CSS state classes
// (recording, transcribing) for visual feedback.
// ============================================================

const voiceControls = document.getElementById("voice-controls");

// Build the mic button
const micBtn = document.createElement("button");
micBtn.type = "button";
micBtn.id   = "mic-btn";
micBtn.setAttribute("aria-label", "Record voice input");

// Use Feather icon if available, otherwise plain text
function getMicIcon(name) {
  if (typeof feather !== "undefined" && feather.icons[name]) {
    return feather.icons[name].toSvg({ width: 12, height: 12, "stroke-width": 2 });
  }
  return "";
}

function setMicState(state) {
  micBtn.classList.remove("recording", "transcribing");
  switch (state) {
    case "idle":
      micBtn.innerHTML = getMicIcon("mic") + " <span>Voice</span>";
      micBtn.setAttribute("aria-label", "Record voice input");
      micBtn.disabled = false;
      break;
    case "recording":
      micBtn.innerHTML = getMicIcon("square") + " <span>Stop</span>";
      micBtn.setAttribute("aria-label", "Stop recording");
      micBtn.classList.add("recording");
      micBtn.disabled = false;
      break;
    case "transcribing":
      micBtn.innerHTML = getMicIcon("loader") + " <span>Processing...</span>";
      micBtn.setAttribute("aria-label", "Transcribing audio");
      micBtn.classList.add("transcribing");
      micBtn.disabled = true;
      break;
  }
}

setMicState("idle");
voiceControls.appendChild(micBtn);

let mediaRecorder;
let audioChunks = [];

// ── Recording logic (UNCHANGED) ─────────────────────────────
micBtn.addEventListener("click", async function () {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    setMicState("transcribing");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks   = [];

    mediaRecorder.ondataavailable = function (event) {
      audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async function () {
      const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
      const formData  = new FormData();
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

      setMicState("idle");
    };

    mediaRecorder.start();
    setMicState("recording");

  } catch (err) {
    // User-friendly message for mic permission denial
    alert("Microphone access is required for voice input. Please allow it in your browser settings.");
    setMicState("idle");
  }
});

// ── Text-to-Speech (UNCHANGED) ───────────────────────────────
window.speakAnswer = function (text) {
  if (!("speechSynthesis" in window)) {
    console.warn("Speech synthesis not supported in this browser.");
    return;
  }

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);

  const langSelect   = document.getElementById("lang-select");
  const currentLang  = langSelect ? langSelect.value : "en";

  const langMap = {
    en: "en-IN",
    hi: "hi-IN",
    ml: "ml-IN",
    ta: "ta-IN"
  };

  utterance.lang  = langMap[currentLang] || "en-IN";
  utterance.rate  = 1.0;
  utterance.pitch = 1.0;

  window.speechSynthesis.speak(utterance);
};

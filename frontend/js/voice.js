/**
 * voice.js
 * --------
 * This file adds two voice features to the WeatherGPT chatbot:
 *
 * 1. SPEECH RECOGNITION (mic button → your voice becomes text)
 *    - Uses the browser's built-in Web Speech API
 *    - Works in Chrome, Edge, and most modern browsers
 *    - No API key needed
 *
 * 2. SPEECH SYNTHESIS (bot reads its answer out loud)
 *    - Uses the browser's built-in speechSynthesis
 *    - Works in all modern browsers
 *    - No API key needed
 *
 * HOW TO USE:
 *    Person 2 (who owns chat.js) needs to add this line inside their
 *    addMessage() function when sender === "bot":
 *
 *        if (sender === "bot" && window.speakAnswer) {
 *            window.speakAnswer(text);
 *        }
 *
 *    The HTML page needs a mic button with id="mic-btn" and
 *    the chat input field with id="user-input".
 */

// ============================================================
//  PART 1: SPEECH RECOGNITION (Voice → Text)
// ============================================================

/**
 * This variable holds the speech recognition object.
 * Think of it as the "ear" that listens to your microphone.
 */
let recognition = null;

/**
 * This variable tracks whether we are currently listening.
 * true = mic is ON, false = mic is OFF.
 */
let isListening = false;

/**
 * Sets up speech recognition. Called once when the page loads.
 *
 * What it does:
 *   - Checks if your browser supports speech recognition
 *   - Creates a "listener" that converts your voice to text
 *   - When you stop speaking, it puts the text into the chat input box
 */
function setupSpeechRecognition() {

    // Check if the browser supports speech recognition.
    // Different browsers call it different names, so we check both.
    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        // If the browser doesn't support it, show a message and stop.
        console.warn("Speech Recognition is not supported in this browser.");
        // Hide the mic button since it won't work
        const micBtn = document.getElementById("mic-btn");
        if (micBtn) micBtn.style.display = "none";
        return;
    }

    // Create the speech recognition object (the "ear").
    recognition = new SpeechRecognition();

    // ---------- Settings ----------
    recognition.lang = "en-IN";        // Listen for English (India accent)
    recognition.continuous = false;     // Stop after one sentence
    recognition.interimResults = false; // Only give us the final result

    // ---------- What happens when speech is recognized ----------
    recognition.onresult = function (event) {
        // 'event.results' contains what the browser heard.
        // We grab the text from the first (and only) result.
        const spokenText = event.results[0][0].transcript;

        // Find the chat input box on the page and put the text there.
        const inputField = document.getElementById("user-input");
        if (inputField) {
            inputField.value = spokenText;

            // --- Auto-submit: trigger the same action as pressing Enter ---
            // This makes it so you speak → text appears → message sends automatically.

            // Try clicking the send button if it exists
            const sendBtn = document.getElementById("send-btn");
            if (sendBtn) {
                sendBtn.click();
            } else {
                // If no send button, simulate pressing Enter in the input field
                const enterEvent = new KeyboardEvent("keypress", {
                    key: "Enter",
                    code: "Enter",
                    keyCode: 13,
                    which: 13,
                    bubbles: true,
                });
                inputField.dispatchEvent(enterEvent);
            }
        }
    };

    // ---------- What happens when listening stops ----------
    recognition.onend = function () {
        isListening = false;
        updateMicButton(false);
    };

    // ---------- What happens if there's an error ----------
    recognition.onerror = function (event) {
        console.error("Speech Recognition Error:", event.error);
        isListening = false;
        updateMicButton(false);
    };
}

/**
 * Toggles the microphone ON or OFF.
 * Called when the user clicks the mic button.
 */
function toggleMic() {
    if (!recognition) {
        alert("Speech recognition is not supported in your browser. Please use Chrome or Edge.");
        return;
    }

    if (isListening) {
        // Mic is currently ON → turn it OFF
        recognition.stop();
        isListening = false;
        updateMicButton(false);
    } else {
        // Mic is currently OFF → turn it ON
        recognition.start();
        isListening = true;
        updateMicButton(true);
    }
}

/**
 * Updates the mic button's appearance to show whether it's active.
 *
 * @param {boolean} active - true if mic is listening, false if not
 */
function updateMicButton(active) {
    const micBtn = document.getElementById("mic-btn");
    if (!micBtn) return;

    if (active) {
        // Mic is ON → make the button look "active" (red, glowing, etc.)
        micBtn.classList.add("mic-active");
        micBtn.title = "Click to stop listening";
    } else {
        // Mic is OFF → normal appearance
        micBtn.classList.remove("mic-active");
        micBtn.title = "Click to speak";
    }
}


// ============================================================
//  PART 2: SPEECH SYNTHESIS (Text → Voice)
// ============================================================

/**
 * Makes the browser read the given text out loud.
 *
 * This function is attached to `window.speakAnswer` so that
 * Person 2's chat.js can call it like:
 *     window.speakAnswer("It will rain tomorrow.")
 *
 * @param {string} text - The text to read aloud
 */
function speakAnswer(text) {
    // If the browser doesn't support speech synthesis, do nothing.
    if (!("speechSynthesis" in window)) {
        console.warn("Speech Synthesis is not supported in this browser.");
        return;
    }

    // If the text is empty, nothing to read.
    if (!text || text.trim() === "") return;

    // Stop any currently-playing speech before starting new one.
    window.speechSynthesis.cancel();

    // Create a new "utterance" — think of it as a script for the browser to read.
    const utterance = new SpeechSynthesisUtterance(text);

    // ---------- Voice Settings ----------
    utterance.lang = "en-IN";   // English (India) accent
    utterance.rate = 1.0;       // Speed: 1.0 = normal, 0.5 = slow, 2.0 = fast
    utterance.pitch = 1.0;      // Pitch: 1.0 = normal
    utterance.volume = 1.0;     // Volume: 0.0 = silent, 1.0 = full

    // Try to find a good English voice on this computer.
    const voices = window.speechSynthesis.getVoices();
    const englishVoice = voices.find(function (v) {
        return v.lang.startsWith("en");
    });
    if (englishVoice) {
        utterance.voice = englishVoice;
    }

    // Speak!
    window.speechSynthesis.speak(utterance);
}

/**
 * Stops any speech that is currently playing.
 * Useful if the user wants to shut the bot up mid-sentence.
 */
function stopSpeaking() {
    if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
    }
}


// ============================================================
//  PART 3: SETUP — Runs when the page loads
// ============================================================

// Make speakAnswer and stopSpeaking available to other scripts (like chat.js).
// "window" means it's accessible from anywhere on the page.
window.speakAnswer = speakAnswer;
window.stopSpeaking = stopSpeaking;
window.toggleMic = toggleMic;

// When the page finishes loading, set everything up.
window.addEventListener("DOMContentLoaded", function () {

    // Set up speech recognition (the mic/ear).
    setupSpeechRecognition();

    // Connect the mic button to our toggleMic function.
    const micBtn = document.getElementById("mic-btn");
    if (micBtn) {
        micBtn.addEventListener("click", toggleMic);
    }

    // Pre-load the list of available voices.
    // Some browsers need a moment to load voices, so we listen for the event.
    if ("speechSynthesis" in window) {
        window.speechSynthesis.onvoiceschanged = function () {
            window.speechSynthesis.getVoices();
        };
    }

    console.log("🎤 Voice module loaded successfully!");
});

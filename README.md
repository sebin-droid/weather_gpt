# 🌦️ WeatherGPT — Conversational AI for Weather Forecasting, Alerts & Climate Information

> **Smart India Hackathon 2026 — Problem Statement SIH26068**
> **Ministry of Earth Sciences (MoES)**

WeatherGPT is a **conversational AI assistant** that makes weather information accessible to everyone. Instead of reading complex weather charts and maps, users can simply **ask questions in plain language** — by typing or speaking — and get accurate, easy-to-understand answers in their preferred language.

---

## ✨ What Does WeatherGPT Do?

| Feature | Description |
|---------|-------------|
| 💬 **AI Chat** | Ask weather questions in natural language — *"Will it rain in Mumbai tomorrow?"* |
| 🌍 **GIS & Maps** | Interactive map showing weather conditions, forecasts, and alerts visually |
| 🚨 **Alerts** | Real-time weather warnings (cyclones, heavy rain, heatwaves, etc.) |
| 🌐 **Multilingual** | Get answers in **13 Indian languages** — Hindi, Tamil, Telugu, Bengali, and more |
| 🎤 **Voice** | Speak your question and hear the answer read aloud — no typing needed |
| 📊 **Climate Info** | Access historical climate data and trends |

### 🔧 How It Works (Architecture)

WeatherGPT is **not** a new AI model built from scratch. It intelligently combines proven existing technologies into a seamless pipeline:

```
User (text/voice) → LLM understands the question → Fetches weather data via APIs
    → Generates a conversational answer → Translates to user's language
    → Displays on map + reads answer aloud
```

- **LLM (Large Language Model)** — Understands natural-language questions and generates human-friendly answers
- **Weather APIs** — Fetches real-time weather data, forecasts, and alerts
- **GIS/Maps** — Plots weather data on interactive maps
- **Translation** — Converts answers into the user's chosen language using Google Translate
- **Voice** — Browser-based speech recognition and text-to-speech (no API key needed)

> **Note:** The current version is a **working proof-of-concept** that demonstrates the complete AI chat + alerts + GIS + multilingual + voice pipeline end-to-end.

---

## 🚀 Getting Started

### Prerequisites

Make sure you have the following installed on your computer:

- [Python 3.10+](https://www.python.org/downloads/) — the programming language our backend is written in
- [Node.js](https://nodejs.org/) (optional) — only if you need to serve the frontend locally
- [Docker](https://www.docker.com/products/docker-desktop/) (optional) — to run everything in containers
- A modern web browser (Chrome or Edge recommended for voice features)

---

### 🖥️ Running the Backend

**Step 1: Open a terminal (Command Prompt / PowerShell)**

**Step 2: Navigate to the project folder**

```bash
cd c:\Hackathon
```

**Step 3: Create a virtual environment (keeps your libraries organized)**

```bash
python -m venv venv
```

**Step 4: Activate the virtual environment**

```bash
# Windows (Command Prompt)
venv\Scripts\activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

**Step 5: Install all required libraries**

```bash
pip install -r requirements.txt
```

**Step 6: Set up environment variables**

Create a file called `.env` in the project root with the required API keys:

```env
OPENAI_API_KEY=your_openai_key_here
WEATHER_API_KEY=your_weather_api_key_here
```

> Ask your team lead for the actual API keys.

**Step 7: Start the backend server**

```bash
uvicorn backend.main:app --reload --port 8000
```

**Step 8: Verify it's running**

Open your browser and go to:

```
http://localhost:8000/docs
```

You should see the **FastAPI Swagger UI** — an interactive page that lists all available API endpoints.

---

### 🌐 Running the Frontend

**Step 1:** Open the `frontend/` folder.

**Step 2:** Open `index.html` in your browser (just double-click it), or serve it locally:

```bash
# Using Python's built-in server
cd frontend
python -m http.server 5500
```

**Step 3:** Open your browser and go to:

```
http://localhost:5500
```

---

### 🐳 Running with Docker

Docker lets you run the entire project without manually installing Python, libraries, or anything else.

**Step 1: Install Docker Desktop**

Download from [docker.com](https://www.docker.com/products/docker-desktop/) and install it.

**Step 2: Build and start the containers**

Open a terminal in the project root and run:

```bash
docker-compose -f docker/docker-compose.yml up --build
```

**Step 3: Access the app**

- Backend API: [http://localhost:8000/docs](http://localhost:8000/docs)

**Step 4: Stop the containers**

Press `Ctrl+C` in the terminal, then run:

```bash
docker-compose -f docker/docker-compose.yml down
```

---

## 📁 Project Structure

```
WeatherGPT/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── routers/
│   │   ├── chat.py              # Chat endpoint (Person 1)
│   │   ├── weather.py           # Weather data endpoint (Person 3)
│   │   ├── alerts.py            # Alerts endpoint (Person 3)
│   │   └── translate.py         # Translation endpoint (Person 5)
│   └── services/
│       ├── llm_service.py       # LLM integration (Person 1)
│       ├── weather_service.py   # Weather API integration (Person 3)
│       └── translation_service.py  # Translation service (Person 5)
├── frontend/
│   ├── index.html               # Main HTML page (Person 2)
│   ├── css/
│   │   └── style.css            # Styling (Person 2)
│   └── js/
│       ├── chat.js              # Chat UI logic (Person 2)
│       ├── map.js               # Map/GIS logic (Person 4)
│       └── voice.js             # Voice input/output (Person 5)
├── docker/
│   ├── Dockerfile.backend       # Docker image recipe (Person 5)
│   └── docker-compose.yml       # Multi-container setup (Person 5)
├── requirements.txt             # Python dependencies
├── .env                         # API keys (not uploaded to GitHub)
└── README.md                    # This file (Person 5)
```

---

## 🌐 Supported Languages

| Code | Language | Code | Language |
|------|----------|------|----------|
| `en` | English | `kn` | Kannada |
| `hi` | Hindi | `ml` | Malayalam |
| `ta` | Tamil | `pa` | Punjabi |
| `te` | Telugu | `ur` | Urdu |
| `bn` | Bengali | `or` | Odia |
| `mr` | Marathi | `as` | Assamese |
| `gu` | Gujarati | | |

---

## 🗺️ Production Roadmap

WeatherGPT is currently a proof-of-concept. Here's how it can evolve into a production-grade system:

### Phase 1 — Live Weather Data Integration
- **IMD (India Meteorological Department) Live Feeds** — Replace mock/API data with real-time data directly from IMD
- **WIS 2.0 (WMO Information System)** — Connect to the World Meteorological Organization's global weather data exchange network for international coverage

### Phase 2 — Advanced Forecasting Models
- **GFS (Global Forecast System)** — Integrate NOAA's global numerical weather prediction model for 16-day forecasts
- **WRF (Weather Research and Forecasting)** — Run high-resolution regional weather simulations for hyper-local forecasts (district/block level)
- **NWP (Numerical Weather Prediction)** — Process actual model outputs instead of relying on third-party APIs

### Phase 3 — Mobile & Scale
- **Native Mobile App** — Build dedicated Android & iOS apps with offline support, push notification alerts, and voice-first interaction
- **Regional Language Voice** — Extend voice recognition and text-to-speech to all supported Indian languages
- **Edge Deployment** — Deploy lightweight models at state/district level for low-latency responses

### Phase 4 — Community & Government Integration
- **Agromet Advisories** — Provide weather-based farming advice in local languages
- **Disaster Management Integration** — Connect with NDMA/SDMA for real-time disaster alerts and evacuation guidance
- **Public API** — Offer a developer API so third-party apps can integrate WeatherGPT

---

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python, FastAPI, Uvicorn |
| **AI/LLM** | OpenAI GPT / equivalent LLM |
| **Weather Data** | OpenWeatherMap API / IMD feeds |
| **Translation** | deep-translator (Google Translate) |
| **Voice** | Web Speech API (browser built-in) |
| **Maps/GIS** | Leaflet.js / OpenLayers |
| **Frontend** | HTML, CSS, JavaScript |
| **Containerization** | Docker, Docker Compose |

---

## 👥 Team

| Person | Responsibility |
|--------|---------------|
| Sebin | Backend AI/Chat — LLM integration, `/chat` endpoint |
| Lekshmi | Frontend UI — Chat interface, HTML/CSS/JS |
| Shahid | Weather, Alerts & Climate — Weather APIs, alerts system |
| Suryakiran | Location & Maps — GIS, interactive map, geolocation |
| Sreehari | Multilingual, Voice, Docker & Docs — Translation, voice I/O, deployment |

---

## 📄 License

This project was built for **Smart India Hackathon 2026** (Problem Statement SIH26068) under the **Ministry of Earth Sciences (MoES)**.

---



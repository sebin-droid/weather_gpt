# 🌦️ WeatherGPT

An AI-powered weather intelligence chatbot that answers natural-language weather questions, shows cities on an interactive map, provides weather alerts, and supports multilingual responses and voice input/output.

## Features

- **AI Chat Interface** — Ask questions like "Will it rain in Kochi tomorrow?" and get friendly, AI-generated answers powered by Groq (LLaMA 3.1)
- **Interactive Map** — Every query pins the city on a Leaflet.js map
- **Weather Alerts** — Automatic warnings for heavy rain, high winds, and heatwaves
- **Climate Trends** — View historical temperature and precipitation data for any city
- **Multilingual Support** — Responses in English, Malayalam, and Hindi
- **Voice Input/Output** — Speak your question and hear the answer read aloud (uses Web Speech API)
- **Dynamic City Search** — Look up any city worldwide using the Open-Meteo geocoding API

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI, Uvicorn |
| AI/LLM | Groq API (LLaMA 3.1 8B) |
| Weather Data | Open-Meteo API (current, forecast, historical) |
| Geocoding | Open-Meteo Geocoding API |
| Translation | deep-translator (Google Translate) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Map | Leaflet.js + OpenStreetMap |
| Voice | Web Speech API (SpeechRecognition + SpeechSynthesis) |
| Deployment | Docker, Docker Compose |

## Quick Start

### Prerequisites
- Python 3.10+
- A free [Groq API key](https://console.groq.com)

### Backend Setup
```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install fastapi uvicorn requests python-dotenv deep-translator
```

Create a `backend/.env` file:
```
GROQ_API_KEY=your_groq_api_key_here
```

Run the backend:
```bash
uvicorn main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

### Frontend Setup
```bash
cd frontend
python -m http.server 5500
```
Open `http://127.0.0.1:5500` in your browser.

### Docker (Alternative)
```bash
cd docker
docker compose up --build
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/chat?question=...&lang=en` | AI-powered weather chat |
| GET | `/weather/current?city=...` | Current weather for a city |
| GET | `/weather/forecast?city=...` | 7-day forecast |
| GET | `/climate/trend?city=...&days=14` | Historical climate data |
| GET | `/alerts?city=...` | Weather alerts/warnings |
| GET | `/location/search?q=...` | Geocode a city name |
| POST | `/translate` | Translate text (JSON body: `{"text": "...", "target_lang": "ml"}`) |

## Production Roadmap

This project is a working proof-of-concept demonstrating the full AI chat + alerts + GIS + multilingual + voice pipeline. A production version would:

- **Connect to IMD/WIS2.0 live feeds** for official Indian Meteorological Department warnings and real-time data streams
- **Run actual NWP models** (GFS/WRF) for high-resolution weather predictions instead of relying solely on Open-Meteo
- **Ship as a native mobile app** (React Native / Flutter) with push notifications for severe weather alerts
- **Add user accounts** with location preferences and personalized weather briefings
- **Implement caching** (Redis) to reduce API calls and improve response times
- **Deploy on cloud infrastructure** (AWS/GCP) with auto-scaling and a CDN for the frontend

## License

MIT

# WeatherGPT 🌦️

An AI-powered weather intelligence web app built as a team hackathon project.
Ask it anything about the weather — it finds your city, fetches real data, shows it on a live map, and even reads the answer aloud.

---

## Team & Responsibilities

| Person | Role | Files Owned |
|--------|------|-------------|
| Person 1 | Backend Lead & AI Chat | `main.py`, AI prompt logic |
| Person 2 | Frontend UI | `frontend/index.html`, `frontend/js/chat.js` |
| Person 3 | Weather & Alerts | `services/weather_service.py` |
| **Person 4** | **Location Search & Map** | `services/location_service.py`, `routers/location.py`, `frontend/js/map.js` |
| Person 5 | Voice & Translation | `frontend/js/voice.js` |

---

## Project Structure

```
weather_gpt/
├── main.py                        # FastAPI entry point (Person 1)
├── requirements.txt               # Python dependencies
├── .gitignore                     # Files excluded from git
│
├── services/
│   ├── location_service.py        # City name → lat/lon geocoding (Person 4)
│   └── weather_service.py         # Weather data from Open-Meteo (Person 3)
│
├── routers/
│   └── location.py                # GET /location/search endpoint (Person 4)
│
├── utils/
│   └── weather_codes.py           # WMO weather code descriptions
│
└── frontend/
    ├── index.html                 # Main UI (Person 2)
    ├── css/
    │   └── style.css              # Styles
    └── js/
        ├── chat.js                # Chat logic (Person 2)
        ├── map.js                 # Interactive Leaflet map (Person 4)
        └── voice.js               # Voice I/O (Person 5)
```

---

## API Endpoints

| Method | Endpoint | Description | Example |
|--------|----------|-------------|---------|
| GET | `/` | Health check | → `{"message": "WeatherGPT Backend is Running!"}` |
| GET | `/location/search?q=<city>` | Geocode a city | → `{"city":"Delhi","country":"India","latitude":28.65,"longitude":77.23}` |
| GET | `/weather?latitude=<lat>&longitude=<lon>` | Current weather by coordinates | → weather JSON |
| GET | `/weather/city?city=<city>` | Current weather by city name | → location + weather JSON |
| GET | `/forecast?city=<city>` | 7-day forecast by city | → location + forecast JSON |

Interactive docs: http://127.0.0.1:8000/docs

---

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/sebin-droid/weather_gpt.git
cd weather_gpt
```

### 2. Create and activate virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the backend
```bash
uvicorn main:app --reload
```
Backend runs at: http://127.0.0.1:8000

### 5. Open the frontend
```bash
cd frontend
python -m http.server 5500
```
Open your browser to: http://127.0.0.1:5500

---

## Person 4 — Location Search & Map

### What I Built

#### `services/location_service.py`
Converts any city name into GPS coordinates using the **Open-Meteo Geocoding API** (free, no API key).

```python
from services.location_service import get_location

result = get_location("Delhi")
# {"city": "Delhi", "country": "India", "latitude": 28.65195, "longitude": 77.23149}
```

#### `routers/location.py`
FastAPI router that exposes `/location/search`:

```
GET http://127.0.0.1:8000/location/search?q=Mumbai
→ {"city": "Mumbai", "country": "India", "latitude": 19.07283, "longitude": 72.88261}
```

#### `frontend/js/map.js`
Interactive **Leaflet.js** map that:
- Starts centered on Kerala (zoom 6)
- Exposes `window.updateMap(location)` — called by `chat.js` when a city is found
- Moves the camera to the found city and drops a labeled pin

### APIs Used

| API | Purpose | Cost |
|-----|---------|------|
| [Open-Meteo Geocoding](https://geocoding-api.open-meteo.com/v1/search) | City → lat/lon | Free, no key |
| [OpenStreetMap / Leaflet](https://leafletjs.com/) | Interactive map tiles | Free |

---

## Git Workflow (for team members)

```bash
# 1. Always work on your feature branch
git checkout feature/<yourname>

# 2. Stage and commit your changes
git add .
git commit -m "Short description of what I did"

# 3. Push to GitHub
git push origin feature/<yourname>

# 4. After a merge window, sync from main
git pull origin main
```

**Branch naming:** `feature/<yourname>` (e.g. `feature/arjun`, `feature/person4-location-map`)

---

## Notebook

A beginner-friendly Jupyter notebook (`WeatherGPT_Person4.ipynb`) is included in the `Hackathon/` folder.
It walks through every step: setup, writing each file, testing, and committing — with explanations for each line of code.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, FastAPI, Uvicorn |
| Geocoding | Open-Meteo Geocoding API (free) |
| Weather Data | Open-Meteo Weather API (free) |
| Map | Leaflet.js + OpenStreetMap |
| Frontend | HTML, CSS, Vanilla JavaScript |
| Version Control | Git + GitHub |

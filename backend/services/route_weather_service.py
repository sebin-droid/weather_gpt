import requests
from datetime import datetime, timedelta
from utils.weather_codes import get_weather_description


def get_hourly_weather(lat, lon, forecast_days=3):
    """
    Fetch hourly weather forecast from Open-Meteo.
    Returns raw hourly data dict with time array and weather arrays.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "relative_humidity_2m",
        ],
        "forecast_days": forecast_days,
        "timezone": "auto",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("hourly", {})
    except Exception as e:
        print(f"Hourly weather error: {e}")
        return {}


def get_weather_at_time(hourly_data, target_time_iso):
    """
    Given hourly forecast data and a target ISO timestamp,
    find the closest matching hour and return weather dict.
    """
    if not hourly_data or "time" not in hourly_data:
        return {}

    times = hourly_data["time"]
    target_time = datetime.fromisoformat(target_time_iso.replace("Z", "+00:00"))

    closest_idx = 0
    min_diff = float("inf")

    for i, time_str in enumerate(times):
        dt = datetime.fromisoformat(time_str)
        diff = abs((target_time.replace(tzinfo=None) - dt.replace(tzinfo=None)).total_seconds())
        if diff < min_diff:
            min_diff = diff
            closest_idx = i

    return {
        "temperature": hourly_data["temperature_2m"][closest_idx],
        "precipitation": hourly_data["precipitation"][closest_idx],
        "wind_speed": hourly_data["wind_speed_10m"][closest_idx],
        "humidity": hourly_data["relative_humidity_2m"][closest_idx],
        "condition": get_weather_description(hourly_data["weather_code"][closest_idx]),
        "weather_code": hourly_data["weather_code"][closest_idx],
    }


def get_route_weather(waypoints, start_time_iso, total_duration_seconds):
    """
    For each waypoint, calculate expected arrival time and
    fetch the weather forecast for that specific time.
    This is TIME-AWARE: each waypoint gets the weather at its arrival time.
    """
    if not waypoints:
        return []

    start_time = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
    total_route_distance = waypoints[-1]["cumulative_distance_km"] if waypoints else 0

    enriched = []

    for wp in waypoints:
        # Calculate what fraction of the journey this waypoint represents
        fraction = wp["cumulative_distance_km"] / total_route_distance if total_route_distance > 0 else 0
        # Estimate travel seconds to this point
        travel_seconds = fraction * total_duration_seconds
        # Calculate arrival time at this waypoint
        arrival_time = start_time + timedelta(seconds=travel_seconds)
        arrival_iso = arrival_time.isoformat()

        # Fetch hourly weather for this location
        hourly_data = get_hourly_weather(wp["lat"], wp["lon"])
        # Extract weather at the ARRIVAL TIME (not start time!)
        weather = get_weather_at_time(hourly_data, arrival_iso)

        enriched_wp = dict(wp)
        enriched_wp["arrival_time"] = arrival_iso
        enriched_wp["weather"] = weather
        enriched.append(enriched_wp)

    return enriched


def _get_icon_and_color(condition, temperature):
    """Map weather condition to emoji icon and hex color."""
    c = condition.lower() if condition else ""

    if "clear" in c:
        icon, color = "☀️", "#f59e0b"
    elif "partly cloudy" in c:
        icon, color = "🌤", "#fbbf24"
    elif "cloudy" in c or "overcast" in c:
        icon, color = "☁️", "#9ca3af"
    elif "heavy rain" in c or "violent" in c:
        icon, color = "🌧", "#1e40af"
    elif "rain" in c or "drizzle" in c or "shower" in c:
        icon, color = "🌧", "#3b82f6"
    elif "thunderstorm" in c:
        icon, color = "⛈", "#7c3aed"
    elif "snow" in c:
        icon, color = "🌨", "#e0f2fe"
    elif "fog" in c:
        icon, color = "🌫", "#d1d5db"
    else:
        icon, color = "🌤", "#9ca3af"

    # Override color for extreme heat
    if temperature is not None and temperature > 38:
        color = "#ef4444"

    return icon, color


def generate_weather_zones(waypoints_with_weather):
    """
    Group consecutive waypoints into weather zones.
    A NEW ZONE starts when the weather CONDITION CHANGES —
    zones are NOT fixed length, they respond to actual weather variation.
    """
    if not waypoints_with_weather:
        return []

    zones = []
    current_zone = None

    for wp in waypoints_with_weather:
        weather = wp.get("weather", {})
        condition = weather.get("condition", "")

        if not current_zone:
            # Start first zone
            icon, color = _get_icon_and_color(condition, weather.get("temperature"))
            current_zone = {
                "from_city": wp.get("city_name", "Unknown"),
                "from_lat": wp["lat"],
                "from_lon": wp["lon"],
                "_start_dist": wp["cumulative_distance_km"],
                "arrival_time": wp["arrival_time"],
                "weather": weather,
                "weather_icon": icon,
                "color": color,
                "_condition": condition,
                "_waypoints": [wp],
            }
        elif current_zone["_condition"] == condition:
            # Same weather — extend current zone
            current_zone["_waypoints"].append(wp)
        else:
            # Weather changed — close current zone, start new one
            last_wp = current_zone["_waypoints"][-1]
            current_zone["to_city"] = wp.get("city_name", "Unknown")
            current_zone["to_lat"] = wp["lat"]
            current_zone["to_lon"] = wp["lon"]
            current_zone["distance_km"] = wp["cumulative_distance_km"] - current_zone["_start_dist"]
            zones.append(current_zone)

            icon, color = _get_icon_and_color(condition, weather.get("temperature"))
            current_zone = {
                "from_city": wp.get("city_name", "Unknown"),
                "from_lat": wp["lat"],
                "from_lon": wp["lon"],
                "_start_dist": wp["cumulative_distance_km"],
                "arrival_time": wp["arrival_time"],
                "weather": weather,
                "weather_icon": icon,
                "color": color,
                "_condition": condition,
                "_waypoints": [wp],
            }

    # Close the last zone
    if current_zone:
        last_wp = current_zone["_waypoints"][-1]
        current_zone["to_city"] = last_wp.get("city_name", "Unknown")
        current_zone["to_lat"] = last_wp["lat"]
        current_zone["to_lon"] = last_wp["lon"]
        current_zone["distance_km"] = last_wp["cumulative_distance_km"] - current_zone["_start_dist"]
        zones.append(current_zone)

    # Clean up internal keys
    for z in zones:
        z.pop("_start_dist", None)
        z.pop("_waypoints", None)
        z.pop("_condition", None)

    return zones


def generate_route_summary(zones, total_distance_km, total_duration_seconds, start_time_iso):
    """
    Generate journey summary with weather breakdown percentages
    (based on zone distances) and warnings for dangerous conditions.
    """
    weather_breakdown = {}
    warnings = []

    for z in zones:
        condition = z["weather"].get("condition", "Unknown") if isinstance(z["weather"], dict) else str(z["weather"])
        dist = z.get("distance_km", 0)
        weather_breakdown[condition] = weather_breakdown.get(condition, 0) + dist

        c_lower = condition.lower()
        if any(w in c_lower for w in ["heavy rain", "thunderstorm", "snow", "fog", "violent"]):
            warnings.append(
                f"{z['weather_icon']} {condition} expected between "
                f"{z['from_city']} and {z['to_city']} "
                f"(around {z.get('arrival_time', 'N/A')})"
            )

    # Convert distances to percentages
    for w in weather_breakdown:
        if total_distance_km > 0:
            weather_breakdown[w] = round((weather_breakdown[w] / total_distance_km) * 100, 1)
        else:
            weather_breakdown[w] = 0

    start_time = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
    arrival_time = start_time + timedelta(seconds=total_duration_seconds)

    return {
        "weather_breakdown": weather_breakdown,
        "warnings": list(set(warnings)),
        "arrival_time": arrival_time.isoformat(),
    }

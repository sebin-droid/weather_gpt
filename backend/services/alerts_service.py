def check_alerts(forecast_data: list):
    """Looks at forecast days and returns a warning message if
    any day crosses a dangerous threshold."""
    alerts = []

    for day in forecast_data:
        if day["rain"] and day["rain"] > 50:
            alerts.append(f"Heavy rain warning on {day['date']} ({day['rain']}mm expected).")

        if day["max_wind_speed"] and day["max_wind_speed"] > 40:
            alerts.append(f"High wind advisory on {day['date']} ({day['max_wind_speed']} km/h).")

        if day["max_temperature"] and day["max_temperature"] > 40:
            alerts.append(f"Heatwave warning on {day['date']} ({day['max_temperature']}°C).")

    return alerts

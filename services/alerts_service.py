def check_alerts(forecast_data: list):
    """
    Looks at the 7-day forecast and returns a list of warning
    messages if any day crosses a dangerous weather threshold.

    Thresholds:
      - Rain > 50 mm  → Heavy rain warning
      - Wind > 40 km/h → High wind advisory
      - Max temp > 40°C → Heatwave warning
    """
    alerts = []

    for day in forecast_data:

        # Heavy rain check
        if day.get("rain") and day["rain"] > 50:
            alerts.append(
                f"Heavy rain warning on {day['date']} "
                f"({day['rain']} mm expected)."
            )

        # High wind check
        if day.get("max_wind_speed") and day["max_wind_speed"] > 40:
            alerts.append(
                f"High wind advisory on {day['date']} "
                f"({day['max_wind_speed']} km/h)."
            )

        # Heatwave check
        if day.get("max_temperature") and day["max_temperature"] > 40:
            alerts.append(
                f"Heatwave warning on {day['date']} "
                f"({day['max_temperature']}°C)."
            )

    return alerts

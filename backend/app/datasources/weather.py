"""Weather-delay signal from Open-Meteo (keyless, no archive burst).

Bulk berths at exposed anchorages lose working time to heavy swell / wind and to
monsoon rain. We turn a 16-day forecast at each discharge port into an expected
number of weather-delay days that flows into the idle-risk and voyage models.
"""

from __future__ import annotations

import logging

from .base import get_json

log = logging.getLogger("freightsight.datasources")

_FORECAST = "https://api.open-meteo.com/v1/forecast"

WIND_STOP_KMH = 46.0     # sustained max wind that halts crane work
RAIN_STOP_MM = 45.0      # daily rain that halts open-hatch bulk handling


def _delay_days(precip: list[float], wind: list[float]) -> float:
    d = 0.0
    for p, w in zip(precip, wind, strict=False):
        p = p or 0.0
        w = w or 0.0
        if w >= WIND_STOP_KMH:
            d += 0.7
        elif w >= WIND_STOP_KMH * 0.8:
            d += 0.3
        if p >= RAIN_STOP_MM:
            d += 0.5
        elif p >= RAIN_STOP_MM * 0.6:
            d += 0.2
    return round(d, 1)


def weather_outlook(lat: float, lon: float) -> dict | None:
    """{expected_delay_days_16d, high_wind_days, heavy_rain_days} or None."""
    fc = get_json(_FORECAST, params={
        "latitude": lat, "longitude": lon, "forecast_days": 16, "timezone": "UTC",
        "daily": "precipitation_sum,wind_speed_10m_max",
    }, ttl_h=6.0, timeout=10.0, retries=2)
    try:
        d = fc["daily"]
        precip, wind = d["precipitation_sum"], d["wind_speed_10m_max"]
        return {
            "expected_delay_days_16d": _delay_days(precip, wind),
            "high_wind_days": sum(1 for w in wind if (w or 0) >= WIND_STOP_KMH * 0.8),
            "heavy_rain_days": sum(1 for p in precip if (p or 0) >= RAIN_STOP_MM * 0.6),
        }
    except Exception as exc:
        log.warning("Open-Meteo parse failed (%.2f,%.2f): %s", lat, lon, exc)
        return None

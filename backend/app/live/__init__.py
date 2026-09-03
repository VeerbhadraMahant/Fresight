"""Phase 3 -- live vessel monitoring.

``ais``    : parse AISStream.io messages + sample the global stream (WebSocket).
``reckon`` : spherical dead-reckoning + nearest-port lookup (pure, no I/O).

The worker (``worker/live.py``) uses both to keep ``positions`` / ``vessels`` /
``voyages`` current; the API reads them via ``routers/map.py``. Everything here
is optional -- with no ``AISSTREAM_API_KEY`` the sampler is a no-op and the map
still shows ports + sea lanes.
"""

from .reckon import bearing_deg, dead_reckon, haversine_nm, nearest_port

__all__ = ["bearing_deg", "dead_reckon", "haversine_nm", "nearest_port"]

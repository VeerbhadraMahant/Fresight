"""Real, keyless public data sources that FreightSight blends into the market model.

  freight_index  -- Breakwave Dry Bulk Shipping ETF (BDRY), a tradeable proxy for
                    the dry-bulk freight cycle                     [Yahoo Finance]
  bunker         -- Brent crude (BZ=F) -> VLSFO estimate           [Yahoo Finance]
  port_activity  -- daily port calls + import volume per port      [IMF PortWatch]
  weather        -- precipitation / wind, history + 16-day forecast  [Open-Meteo]

Every call is best-effort with an on-disk cache and a hard deadline; if a source
is unreachable the model falls back to its synthetic component and the
provenance record says so.
"""

from .provider import RealData, load_real_data, snapshot_dict

__all__ = ["RealData", "load_real_data", "snapshot_dict"]

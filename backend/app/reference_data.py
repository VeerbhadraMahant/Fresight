"""Static reference data: ports, vessel classes, trade routes, commodities.

All figures are approximate, drawn from public port-authority pages, Wikipedia,
and trade press, and are intended for a decision-support *prototype* -- not for
operational chartering. Sources are noted inline. Where a public figure was not
found, a conservative industry-typical value is used and flagged `assumed`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal

Region = Literal["Australia", "USA", "Mozambique", "Indonesia", "Russia", "India-EastCoast"]


# --------------------------------------------------------------------------- #
# Vessel classes
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class VesselClass:
    name: str
    dwt: int                 # summer deadweight, t
    loa: float               # length overall, m
    beam: float              # m
    scantling_draft: float   # max design draft, m
    laden_speed_kn: float
    ballast_speed_kn: float
    bunker_sea_tpd: float    # VLSFO consumption at sea, t/day
    bunker_port_tpd: float
    geared: bool             # has own cranes (can work draft-restricted / gearless berths)
    typical_tce_usd_day: int  # long-run average time-charter-equivalent, calm market


VESSEL_CLASSES: dict[str, VesselClass] = {
    v.name: v
    for v in [
        VesselClass("Handysize", 32_000, 180, 28.0, 10.0, 12.5, 13.0, 18.0, 3.0, True, 11_500),
        VesselClass("Supramax", 58_000, 199, 32.3, 12.8, 13.0, 13.5, 26.0, 4.0, True, 14_500),
        VesselClass("Panamax", 76_000, 229, 32.2, 14.1, 13.0, 13.5, 30.0, 4.5, False, 15_500),
        VesselClass("Kamsarmax", 82_000, 229, 32.3, 14.4, 13.0, 13.5, 31.0, 4.5, False, 16_500),
        VesselClass("Capesize", 180_000, 292, 45.0, 18.2, 12.8, 13.2, 42.0, 6.0, False, 22_000),
    ]
}

VESSEL_ORDER = ["Handysize", "Supramax", "Panamax", "Kamsarmax", "Capesize"]


# --------------------------------------------------------------------------- #
# Ports
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Port:
    code: str
    name: str
    country: str
    region: Region
    role: Literal["load", "discharge", "both"]
    lat: float
    lon: float
    max_draft_m: float          # max permissible sailing draft for dry bulk
    max_loa_m: float
    max_beam_m: float
    max_dwt: int
    berth_handling_tph: float   # effective loading/discharge rate, tonnes/hour (coal, mechanised)
    congestion_base_days: float  # long-run average waiting time before berth
    transload: bool = False      # cargo worked at anchorage via floating cranes / STS
    notes: str = ""
    source: str = ""

    @property
    def handling_tpd(self) -> float:
        return self.berth_handling_tph * 24.0


# East Coast India -- discharge ports named in the problem statement
_ECI_PORTS = [
    Port("INPRT", "Paradip", "India", "India-EastCoast", "discharge", 20.26, 86.67,
         16.5, 300, 46, 175_000, 1600, 2.2,
         notes="Mechanised coal berths; PPA handles Capesize (draft-limited to ~150k t intake at 16.5 m).",
         source="paradipport.gov.in/berth_spec"),
    Port("INVTZ", "Visakhapatnam (Outer Harbour)", "India", "India-EastCoast", "both", 17.68, 83.28,
         17.0, 390, 50, 200_000, 1400, 2.6,
         notes="Outer Harbour + SPM; super-Cape up to 200k DWT, draft to ~18.1 m at SPM.",
         source="vizagport.com allowable LOA/Beam/Draft"),
    Port("INGVR", "Gangavaram", "India", "India-EastCoast", "discharge", 17.63, 83.23,
         18.0, 325, 55, 200_000, 1600, 1.8,
         notes="Water depth to 21 m; fully-laden super-Cape capable.",
         source="en.wikipedia.org/wiki/Gangavaram_Port"),
    Port("INGPR", "Gopalpur", "India", "India-EastCoast", "discharge", 19.27, 84.92,
         14.2, 290, 45, 100_000, 950, 1.5,
         notes="Cape geared self-dischargers to ~14.5 m; berths GCB1-3 at 14.2 m.",
         source="gopalpurports.in max permissible LOA/Beam/Draft"),
    Port("INDHA", "Dhamra", "India", "India-EastCoast", "discharge", 20.78, 87.00,
         18.0, 290, 47, 180_000, 1500, 1.6,
         notes="18 m draught, 180k DWT Capesize.",
         source="en.wikipedia.org/wiki/Dhamra_Port ; shipnext.com"),
    Port("INSAN", "Sagar / Sandheads", "India", "India-EastCoast", "discharge", 21.15, 88.05,
         10.5, 260, 40, 90_000, 650, 3.0, transload=True,
         notes="Anchorage transloading point for the Hooghly; floating-crane lighterage to Haldia/Kolkata.",
         source="assumed from Hooghly estuary pilotage practice"),
    Port("INHAL", "Haldia", "India", "India-EastCoast", "discharge", 22.03, 88.09,
         9.1, 230, 32.5, 60_000, 650, 3.4,
         notes="Tidal riverine dock; Panamax part-laden only, max ~8.5 m sustained sailing draft.",
         source="en.wikipedia.org/wiki/Haldia_Dock_Complex"),
]

# Origin load ports
_ORIGIN_PORTS = [
    # Australia
    Port("AUHPT", "Hay Point", "Australia", "Australia", "load", -21.28, 149.30,
         17.4, 300, 50, 200_000, 5800, 1.4,
         notes="Metallurgical + thermal coal; two of the world's largest coal terminals (DBCT + HPCT).",
         source="nqbp.com.au ; ballastmarkets.com/ports/hay-point"),
    Port("AUNTL", "Newcastle", "Australia", "Australia", "load", -32.92, 151.79,
         16.2, 300, 50, 200_000, 5200, 1.8,
         notes="World's largest coal export port (thermal); Hunter Valley Coal Chain.",
         source="en.wikipedia.org/wiki/Port_of_Newcastle"),
    Port("AUDBY", "Dalrymple Bay", "Australia", "Australia", "load", -21.25, 149.32,
         18.1, 305, 50, 210_000, 5500, 1.6,
         notes="Deepwater Capesize coal terminal adjacent to Hay Point.",
         source="assumed from NQBP declared depths"),
    # USA
    Port("USORF", "Hampton Roads (Norfolk)", "USA", "USA", "load", 36.92, -76.33,
         15.2, 300, 48, 175_000, 2500, 2.0,
         notes="Lamberts Point / Pier IX coal piers; ~50 ft channel.",
         source="assumed from USACE Norfolk Harbor 50 ft project"),
    Port("USBAL", "Baltimore (Curtis Bay)", "USA", "USA", "load", 39.22, -76.58,
         15.2, 290, 46, 150_000, 1900, 2.2,
         notes="CSX Curtis Bay + CNX Marine coal terminals.",
         source="assumed from Baltimore Harbor 50 ft channel"),
    # Mozambique
    Port("MZMPM", "Maputo", "Mozambique", "Mozambique", "load", -25.97, 32.57,
         14.2, 280, 44, 120_000, 1100, 2.4,
         notes="Coal + chrome + ferro; channel dredged to ~14.2-14.7 m, Panamax / part-laden Cape.",
         source="assumed from Port of Maputo declared depth"),
    Port("MZBEW", "Beira", "Mozambique", "Mozambique", "load", -19.83, 34.84,
         12.0, 240, 40, 80_000, 850, 3.0,
         notes="Access channel siltation-constrained; Handy/Supramax coal from Moatize via Sena line.",
         source="assumed from Cornelder de Mocambique channel notices"),
    # Indonesia
    Port("IDMBR", "Muara Berau (East Kalimantan)", "Indonesia", "Indonesia", "load", -0.33, 117.42,
         17.5, 300, 50, 200_000, 1300, 2.8, transload=True,
         notes="Anchorage transloading: mother vessels loaded by floating cranes / barges.",
         source="16marine.co.id guidance to loading coal in Kalimantan"),
    Port("IDTBN", "Taboneo (South Kalimantan)", "Indonesia", "Indonesia", "load", -3.68, 114.42,
         16.5, 300, 50, 190_000, 1150, 3.0, transload=True,
         notes="Banjarmasin/Taboneo anchorage STS coal loading.",
         source="gem.wiki Banjamarsin Port"),
    # Russia
    Port("RUVYP", "Vostochny", "Russia", "Russia", "load", 42.75, 133.08,
         16.5, 300, 48, 170_000, 3000, 2.0,
         notes="Far East mechanised coal terminal (Nakhodka).",
         source="assumed from Port Vostochny coal complex declared depth"),
    Port("RUULU", "Ust-Luga", "Russia", "Russia", "load", 59.67, 28.40,
         14.4, 260, 42, 120_000, 2200, 2.4,
         notes="Baltic coal terminal; Suez routing to East Coast India.",
         source="assumed from Ust-Luga declared depth"),
]

PORTS: dict[str, Port] = {p.code: p for p in (_ECI_PORTS + _ORIGIN_PORTS)}

DISCHARGE_PORTS = [p.code for p in _ECI_PORTS]
LOAD_PORTS = [p.code for p in _ORIGIN_PORTS]


# --------------------------------------------------------------------------- #
# Commodities
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Commodity:
    name: str
    stowage_factor_m3_t: float   # affects whether cargo is deadweight- or volume-limited
    density_bucket: str
    default_parcel_range_t: tuple[int, int]


COMMODITIES: dict[str, Commodity] = {
    c.name: c
    for c in [
        Commodity("Thermal Coal", 1.20, "heavy-grain", (40_000, 160_000)),
        Commodity("Coking Coal", 1.25, "heavy-grain", (55_000, 145_000)),
        Commodity("Iron Ore", 0.40, "heavy", (60_000, 180_000)),
        Commodity("Bauxite", 0.85, "heavy", (45_000, 170_000)),
        Commodity("Limestone", 0.75, "heavy", (35_000, 120_000)),
    ]
}


# --------------------------------------------------------------------------- #
# Trade routes  (great-circle-ish sailing distances, nautical miles, one way)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Route:
    id: str
    origin: str           # port code
    destination: str      # port code
    distance_nm: int
    canal: Literal["none", "suez", "good-hope"] = "none"
    lane: str = ""        # human label
    # per-route calibration of the fundamental freight level, multiplier on the
    # voyage-economics model output (captures cargo imbalance / backhaul value).
    freight_calibration: float = 1.0
    seasonality_profile: str = "monsoon"  # key into SEASONALITY
    demand_weight: float = 1.0            # relative parcel flow on this lane


ROUTES: dict[str, Route] = {}


def _add_route(r: Route) -> None:
    ROUTES[r.id] = r


_add_route(Route("AUHPT-INPRT", "AUHPT", "INPRT", 6300, "none", "Hay Point -> Paradip", 0.90, "monsoon", 1.4))
_add_route(Route("AUHPT-INVTZ", "AUHPT", "INVTZ", 6150, "none", "Hay Point -> Visakhapatnam", 0.91, "monsoon", 1.2))
_add_route(Route("AUNTL-INPRT", "AUNTL", "INPRT", 7050, "none", "Newcastle -> Paradip", 0.92, "monsoon", 1.1))
_add_route(Route("AUNTL-INGVR", "AUNTL", "INGVR", 6900, "none", "Newcastle -> Gangavaram", 0.92, "monsoon", 1.0))
_add_route(Route("AUDBY-INDHA", "AUDBY", "INDHA", 6350, "none", "Dalrymple Bay -> Dhamra", 0.90, "monsoon", 1.0))
_add_route(Route("USORF-INPRT", "USORF", "INPRT", 12500, "good-hope", "Hampton Roads -> Paradip", 1.12, "atlantic", 0.6))
_add_route(Route("USBAL-INVTZ", "USBAL", "INVTZ", 12650, "good-hope", "Baltimore -> Visakhapatnam", 1.12, "atlantic", 0.5))
_add_route(Route("MZMPM-INPRT", "MZMPM", "INPRT", 5250, "none", "Maputo -> Paradip", 0.85, "indian-ocean", 0.7))
_add_route(Route("MZBEW-INVTZ", "MZBEW", "INVTZ", 5050, "none", "Beira -> Visakhapatnam", 0.88, "indian-ocean", 0.5))
_add_route(Route("IDMBR-INPRT", "IDMBR", "INPRT", 3250, "none", "Muara Berau -> Paradip", 0.70, "monsoon", 1.6))
_add_route(Route("IDMBR-INVTZ", "IDMBR", "INVTZ", 3050, "none", "Muara Berau -> Visakhapatnam", 0.70, "monsoon", 1.5))
_add_route(Route("IDMBR-INHAL", "IDMBR", "INHAL", 3450, "none", "Muara Berau -> Haldia", 0.74, "monsoon", 1.3))
_add_route(Route("IDTBN-INGPR", "IDTBN", "INGPR", 3150, "none", "Taboneo -> Gopalpur", 0.72, "monsoon", 1.0))
_add_route(Route("IDMBR-INSAN", "IDMBR", "INSAN", 3400, "none", "Muara Berau -> Sagar/Sandheads", 0.75, "monsoon", 1.1))
_add_route(Route("RUVYP-INVTZ", "RUVYP", "INVTZ", 5600, "none", "Vostochny -> Visakhapatnam", 0.92, "pacific", 0.6))
_add_route(Route("RUULU-INPRT", "RUULU", "INPRT", 8200, "suez", "Ust-Luga -> Paradip", 1.05, "atlantic", 0.4))


# --------------------------------------------------------------------------- #
# Seasonality profiles -- multiplicative monthly factors on freight demand/rate.
# Captures Indian coal restocking ahead of winter/summer peaks, SW-monsoon
# weather delays (Jun-Sep) on the East Coast, and origin-side patterns.
# index 0 = January ... 11 = December
# --------------------------------------------------------------------------- #
SEASONALITY: dict[str, list[float]] = {
    # East-Coast-India-facing lanes: pre-monsoon stocking peak (Mar-May), monsoon
    # softness + weather premiums (Jul-Sep), Q4 restock.
    "monsoon": [1.02, 1.03, 1.08, 1.10, 1.07, 0.98, 0.93, 0.94, 0.97, 1.04, 1.06, 1.05],
    "indian-ocean": [1.03, 1.04, 1.06, 1.05, 1.02, 0.99, 0.95, 0.95, 0.98, 1.03, 1.05, 1.05],
    "atlantic": [1.06, 1.05, 1.03, 0.99, 0.97, 0.96, 0.97, 0.99, 1.02, 1.05, 1.07, 1.08],
    "pacific": [1.05, 1.04, 1.01, 0.98, 0.97, 0.98, 1.00, 1.01, 1.02, 1.03, 1.04, 1.05],
}


# --------------------------------------------------------------------------- #
# Bunker (VLSFO) price anchor, USD/t.  Used by the voyage-economics model and
# the synthetic market engine as a common macro driver.
# --------------------------------------------------------------------------- #
BUNKER_ANCHOR_USD_T = 560.0


def route_public_view(r: Route) -> dict:
    o, d = PORTS[r.origin], PORTS[r.destination]
    return {
        "id": r.id,
        "lane": r.lane,
        "origin": {"code": o.code, "name": o.name, "country": o.country, "region": o.region},
        "destination": {"code": d.code, "name": d.name, "region": d.region},
        "distance_nm": r.distance_nm,
        "canal": r.canal,
        "seasonality_profile": r.seasonality_profile,
    }


def port_public_view(p: Port) -> dict:
    d = asdict(p)
    d["handling_tpd"] = round(p.handling_tpd)
    return d


def vessel_public_view(v: VesselClass) -> dict:
    return asdict(v)

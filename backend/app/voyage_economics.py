"""Bottom-up voyage-economics model.

Turns a route + vessel + market inputs (bunker price, time-charter-equivalent
hire) into an estimated *fundamental* freight level in USD per tonne of cargo.

This is deliberately a transparent, auditable spreadsheet-style estimate -- the
same maths a chartering desk does by hand -- not a black box. The synthetic
market engine layers stochastic dynamics on top of this fundamental; the
forecasting models are trained on the resulting series.
"""

from __future__ import annotations

from dataclasses import dataclass

from .reference_data import PORTS, ROUTES, VESSEL_CLASSES, Port, Route, VesselClass

COMMISSION = 0.0375          # address commission + brokerage on gross freight
PORT_TURN_DAYS = 2.0         # berthing, survey, draft-survey, shifting buffer per voyage
BALLAST_DISTANCE_RATIO = 1.0  # repositioning leg as a fraction of laden distance

# Canal transit cost (USD) and added time (days), rough order of magnitude.
CANAL_TOLL = {
    "none": (0.0, 0.0),
    "good-hope": (0.0, 0.0),          # extra distance already baked into route length
    "suez": (0.0, 1.0),              # toll added per-vessel below (scales with NT ~ dwt)
}


def _suez_toll(dwt: int) -> float:
    # very rough: ~USD 5.5 per dwt for a laden bulker transit incl. SCNT factors
    return 5.5 * dwt


def _port(code: str):
    """Curated ``Port`` if we have one, else the global registry's ``ResolvedPort``
    (same draft / handling fields), so any worldwide pair can be costed."""
    p = PORTS.get(code)
    if p is not None:
        return p
    from .geo import ports as _reg  # local import -> no import cycle at module load
    rp = _reg.get(code)
    if rp is None:
        raise KeyError(code)
    return rp


def cargo_intake(vessel: VesselClass, load_port: Port, disch_port: Port,
                 requested_t: float | None = None) -> float:
    """Max liftable parcel given deadweight and the draft limit at both ends."""
    # deadweight available for cargo after bunkers/stores/constants (~6%)
    dwt_cap = vessel.dwt * 0.94
    # draft-limited intake: linear scaling of deadweight with the governing draft
    gov_draft = min(load_port.max_draft_m, disch_port.max_draft_m, vessel.scantling_draft)
    draft_ratio = max(0.45, min(1.0, gov_draft / vessel.scantling_draft))
    draft_cap = vessel.dwt * 0.94 * draft_ratio
    cap = min(dwt_cap, draft_cap)
    if requested_t is not None:
        return min(cap, requested_t)
    return cap


@dataclass
class VoyageBreakdown:
    route_id: str
    vessel: str
    cargo_t: float
    sea_days: float
    port_days: float
    total_days: float
    hire_cost: float
    bunker_cost: float
    port_dues: float
    canal_cost: float
    gross_freight: float
    freight_usd_t: float

    def as_dict(self) -> dict:
        return {
            "route_id": self.route_id,
            "vessel": self.vessel,
            "cargo_t": round(self.cargo_t),
            "sea_days": round(self.sea_days, 1),
            "port_days": round(self.port_days, 1),
            "total_days": round(self.total_days, 1),
            "cost_breakdown_usd": {
                "hire": round(self.hire_cost),
                "bunkers": round(self.bunker_cost),
                "port_dues": round(self.port_dues),
                "canal": round(self.canal_cost),
            },
            "gross_freight_usd": round(self.gross_freight),
            "freight_usd_per_t": round(self.freight_usd_t, 2),
        }


def estimate_voyage(route: Route, vessel: VesselClass, bunker_usd_t: float,
                    tce_usd_day: float, requested_t: float | None = None) -> VoyageBreakdown:
    lp, dp = _port(route.origin), _port(route.destination)
    cargo = cargo_intake(vessel, lp, dp, requested_t)

    laden_days = route.distance_nm / (vessel.laden_speed_kn * 24.0)
    ballast_days = (route.distance_nm * BALLAST_DISTANCE_RATIO) / (vessel.ballast_speed_kn * 24.0)
    _, canal_days = CANAL_TOLL[route.canal]
    sea_days = laden_days + ballast_days + canal_days

    load_days = cargo / lp.handling_tpd
    disch_days = cargo / dp.handling_tpd
    port_days = load_days + disch_days + PORT_TURN_DAYS

    total_days = sea_days + port_days

    hire_cost = tce_usd_day * total_days
    bunker_cost = bunker_usd_t * (
        vessel.bunker_sea_tpd * sea_days
        + vessel.bunker_port_tpd * port_days
    )
    port_dues = (45_000 + 0.55 * vessel.dwt) * 2.0
    canal_cost = _suez_toll(vessel.dwt) if route.canal == "suez" else 0.0

    net = hire_cost + bunker_cost + port_dues + canal_cost
    gross_freight = net / (1.0 - COMMISSION)
    freight_usd_t = gross_freight / cargo * route.freight_calibration

    return VoyageBreakdown(
        route_id=route.id, vessel=vessel.name, cargo_t=cargo,
        sea_days=sea_days, port_days=port_days, total_days=total_days,
        hire_cost=hire_cost, bunker_cost=bunker_cost, port_dues=port_dues,
        canal_cost=canal_cost, gross_freight=gross_freight, freight_usd_t=freight_usd_t,
    )


def fundamental_freight_usd_t(route_id: str, vessel_name: str, bunker_usd_t: float,
                              tce_usd_day: float) -> float:
    r = ROUTES[route_id]
    v = VESSEL_CLASSES[vessel_name]
    return estimate_voyage(r, v, bunker_usd_t, tce_usd_day).freight_usd_t

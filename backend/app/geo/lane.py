"""Generic (any-port-to-any-port) voyage-economics for the global lane endpoint.

Mirrors ``app.voyage_economics`` but is parameterised on :class:`ResolvedPort`
and a sea-route distance instead of the curated ``Route`` / ``ROUTES`` table, so
it works for arbitrary port pairs. Results are flagged ``calibrated: false`` --
there is no per-lane cargo-imbalance calibration factor for an unknown lane.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..reference_data import VESSEL_CLASSES, VESSEL_ORDER, VesselClass
from .ports import ResolvedPort
from .searoute import sea_route

COMMISSION = 0.0375
PORT_TURN_DAYS = 2.0
BALLAST_DISTANCE_RATIO = 1.0

# Panama transit ceilings (Neopanamax): beam ~49 m, tropical fresh-water draft ~15.2 m.
PANAMA_MAX_BEAM = 49.0
PANAMA_MAX_DRAFT = 15.2
PANAMA_ALT_DETOUR = 1.35  # rough distance penalty when a vessel can't use the canal the graph picked


def _canal_from_via(via: list[str]) -> str:
    j = " ".join(via)
    if "SUEZ" in j:
        return "suez"
    if "PANAMA" in j:
        return "panama"
    return "none"


def _canal_cost_days(canal: str, dwt: int) -> tuple[float, float]:
    if canal == "suez":
        return 5.5 * dwt, 1.0
    if canal == "panama":
        return max(300_000.0, 3.0 * dwt), 1.0
    return 0.0, 0.0


def _cargo_intake(vessel: VesselClass, gov_draft: float, requested_t: float | None) -> float:
    dwt_cap = vessel.dwt * 0.94
    draft_ratio = max(0.45, min(1.0, gov_draft / vessel.scantling_draft))
    cap = min(dwt_cap, vessel.dwt * 0.94 * draft_ratio)
    return min(cap, requested_t) if requested_t is not None else cap


def _feasibility(o: ResolvedPort, d: ResolvedPort, v: VesselClass) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for label, p in (("load", o), ("disch", d)):
        if v.loa > p.max_loa_m + 1:
            reasons.append(f"LOA {v.loa:.0f} m > {p.name} limit {p.max_loa_m:.0f} m")
        if v.beam > p.max_beam_m + 0.3:
            reasons.append(f"beam {v.beam:.1f} m > {p.name} limit {p.max_beam_m:.1f} m")
        gov = min(o.max_draft_m, d.max_draft_m)
        if v.scantling_draft > gov + 4.0 and not (o.transload or d.transload):
            reasons.append(f"governing draft {gov:.1f} m too shallow for laden {v.name} ({label})")
    # de-dup while keeping order
    seen: set[str] = set()
    uniq = [r for r in reasons if not (r in seen or seen.add(r))]
    return (len(uniq) == 0), uniq


@dataclass
class LaneOption:
    vessel: str
    feasible: bool
    reasons: list[str]
    intake_t: float
    shipments_required: int
    governing_draft_m: float
    distance_nm: float
    canal: str
    sea_days: float
    port_days: float
    total_days: float
    freight_usd_per_t: float
    delivered_cost_usd_per_t: float
    estimated_campaign_cost_usd: float
    co2_kt_campaign: float
    co2_g_per_t_nm: float
    notes: list[str]

    def as_dict(self) -> dict:
        return {
            "vessel": self.vessel,
            "feasible": self.feasible,
            "reasons": self.reasons,
            "intake_t": round(self.intake_t),
            "shipments_required": self.shipments_required,
            "governing_draft_m": round(self.governing_draft_m, 1),
            "distance_nm": round(self.distance_nm),
            "canal": self.canal,
            "sea_days": round(self.sea_days, 1),
            "port_days": round(self.port_days, 1),
            "total_days": round(self.total_days, 1),
            "freight_usd_per_t": round(self.freight_usd_per_t, 2),
            "delivered_cost_usd_per_t": round(self.delivered_cost_usd_per_t, 2),
            "estimated_campaign_cost_usd": round(self.estimated_campaign_cost_usd),
            "co2_kt_campaign": round(self.co2_kt_campaign, 1),
            "co2_g_per_t_nm": round(self.co2_g_per_t_nm, 1),
            "notes": self.notes,
        }


def _one_option(
    o: ResolvedPort, d: ResolvedPort, name: str, *,
    base_distance_nm: float, base_canal: str, base_via: list[str],
    bunker_usd_t: float, tce_usd_day: float, cargo_volume_t: float,
) -> LaneOption:
    v = VESSEL_CLASSES[name]
    feasible, reasons = _feasibility(o, d, v)
    notes: list[str] = []

    distance_nm, canal = base_distance_nm, base_canal
    if base_canal == "panama" and (v.beam > PANAMA_MAX_BEAM or v.scantling_draft > PANAMA_MAX_DRAFT):
        distance_nm = base_distance_nm * PANAMA_ALT_DETOUR
        canal = "none"
        notes.append("too large for the Panama Canal the route graph selected; "
                     "distance is a rough Cape/Suez re-route estimate")

    gov_draft = min(o.max_draft_m, d.max_draft_m, v.scantling_draft)
    intake = _cargo_intake(v, gov_draft, None)
    shipments = max(1, math.ceil(cargo_volume_t / max(intake, 1.0)))

    laden_days = distance_nm / (v.laden_speed_kn * 24.0)
    ballast_days = distance_nm * BALLAST_DISTANCE_RATIO / (v.ballast_speed_kn * 24.0)
    canal_cost, canal_days = _canal_cost_days(canal, v.dwt)
    sea_days = laden_days + ballast_days + canal_days

    load_days = intake / o.handling_tpd
    disch_days = intake / d.handling_tpd
    port_days = load_days + disch_days + PORT_TURN_DAYS
    total_days = sea_days + port_days

    hire = tce_usd_day * total_days
    bunkers = bunker_usd_t * (v.bunker_sea_tpd * sea_days + v.bunker_port_tpd * port_days)
    port_dues = (45_000 + 0.55 * v.dwt) * 2.0
    net = hire + bunkers + port_dues + canal_cost
    gross_freight = net / (1.0 - COMMISSION)
    freight_t = gross_freight / max(intake, 1.0)

    delivered_t = freight_t  # no commodity handling / financing layer at this altitude
    campaign_cost = delivered_t * cargo_volume_t

    # CO2: 3.114 t CO2 / t VLSFO (IMO). Campaign burns fuel per shipment.
    fuel_per_shipment = v.bunker_sea_tpd * sea_days + v.bunker_port_tpd * port_days
    co2_campaign_t = fuel_per_shipment * shipments * 3.114
    tonne_nm = cargo_volume_t * distance_nm
    co2_g_per_t_nm = (co2_campaign_t * 1_000_000.0) / tonne_nm if tonne_nm else 0.0

    if not any("panama" in n.lower() for n in notes) and base_via:
        notes.append("via " + " - ".join(w for w in base_via if w not in ("origin", "destination")))

    return LaneOption(
        vessel=name, feasible=feasible, reasons=reasons, intake_t=intake,
        shipments_required=shipments, governing_draft_m=gov_draft,
        distance_nm=distance_nm, canal=canal, sea_days=sea_days, port_days=port_days,
        total_days=total_days, freight_usd_per_t=freight_t, delivered_cost_usd_per_t=delivered_t,
        estimated_campaign_cost_usd=campaign_cost, co2_kt_campaign=co2_campaign_t / 1000.0,
        co2_g_per_t_nm=co2_g_per_t_nm, notes=notes,
    )


def analyse_lane(
    origin: ResolvedPort, destination: ResolvedPort, *,
    bunker_usd_t: float, tce_by_vessel: dict[str, float],
    commodity: str = "Thermal Coal", cargo_volume_t: float = 150_000.0,
) -> dict:
    route = sea_route(origin.lat, origin.lon, destination.lat, destination.lon,
                      origin.basin, destination.basin)
    canal = _canal_from_via(route.via)

    options = [
        _one_option(
            origin, destination, name,
            base_distance_nm=route.distance_nm, base_canal=canal, base_via=route.via,
            bunker_usd_t=bunker_usd_t, tce_usd_day=tce_by_vessel.get(name, VESSEL_CLASSES[name].typical_tce_usd_day),
            cargo_volume_t=cargo_volume_t,
        ).as_dict()
        for name in VESSEL_ORDER
    ]
    feasible = [o for o in options if o["feasible"]]
    feasible.sort(key=lambda o: o["delivered_cost_usd_per_t"])
    recommendation = feasible[0] if feasible else None

    return {
        "origin": origin.to_public(),
        "destination": destination.to_public(),
        "commodity": commodity,
        "cargo_volume_t": round(cargo_volume_t),
        "calibrated": False,
        "calibration_note": (
            "Generic voyage-economics estimate for an uncalibrated global lane: "
            "sea distance from the waypoint-graph model, freight built bottom-up from "
            "current bunker + time-charter-equivalent hire. No per-lane cargo-imbalance "
            "calibration is applied (unlike the curated East-Coast-India lanes)."
        ),
        "route": {
            "distance_nm": round(route.distance_nm),
            "canal": canal,
            "via": route.via,
            "geometry": route.geometry,
            "method": route.method,
        },
        "market_inputs": {
            "vlsfo_usd_t": round(bunker_usd_t, 1),
            "tce_usd_day": {k: round(v) for k, v in tce_by_vessel.items()},
        },
        "options": options,
        "recommendation": recommendation,
    }

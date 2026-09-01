"""Pydantic request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VesselOptimiseRequest(BaseModel):
    origin: str = Field(..., description="load port code, e.g. AUHPT")
    destination: str = Field(..., description="East Coast India discharge port code, e.g. INPRT")
    commodity: str = Field("Thermal Coal")
    cargo_volume_t: float = Field(..., gt=0, description="total campaign tonnage")
    laycan_month: int | None = Field(None, ge=1, le=12)
    use_forecast_horizon_days: int | None = Field(
        None, description="if set, price freight off the forecast at this horizon instead of latest")


class TimingRequest(BaseModel):
    route_id: str
    vessel: str
    contract_duration_months: int = Field(3, ge=1, le=18)
    volume_t: float = Field(150_000, gt=0)
    risk_aversion: float = Field(0.35, ge=0, le=2)


class ScenarioRequest(BaseModel):
    """One-shot 'run the whole desk' request used by the dashboard."""
    origin: str
    destination: str
    commodity: str = "Thermal Coal"
    cargo_volume_t: float = 150_000
    contract_duration_months: int = 3
    laycan_month: int | None = None
    vessel: str | None = Field(None, description="pin a vessel; otherwise the optimiser's pick is used")
    forecast_horizon_days: int = 90


class RequirementItem(BaseModel):
    origin: str
    destination: str
    commodity: str = "Thermal Coal"
    tonnes: float = Field(..., gt=0)
    laycan_month: int | None = Field(None, ge=1, le=12)


class PlanRequest(BaseModel):
    """A forward procurement plan: several cargo requirements over a horizon."""
    requirements: list[RequirementItem] = Field(..., min_length=1)
    horizon_months: int = Field(6, ge=1, le=18)

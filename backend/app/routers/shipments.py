"""Shipment-tracking endpoints (Phase D).

  GET    /api/shipments              list, each with its latest valuation
  POST   /api/shipments              create (captures a baseline delivered cost)
  GET    /api/shipments/{ref}        full picture: analysis + live vessel + cost history
  PATCH  /api/shipments/{ref}        status / vessel assignment / re-baseline
  DELETE /api/shipments/{ref}        remove
  POST   /api/shipments/{ref}/revalue   value now and append a cost point

Needs ``DATABASE_URL``. Without one every route returns ``{"enabled": false}``
(200) so the frontend can show a clear "connect a database" state instead of an
error, matching the live-map endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import shipments as svc
from ..db import DB_ENABLED
from ..schemas import ShipmentCreate, ShipmentPatch

router = APIRouter(prefix="/api/shipments", tags=["shipments"])

_DISABLED = {"enabled": False, "reason": "no database configured (DATABASE_URL)"}


@router.get("")
def list_shipments():
    if not DB_ENABLED:
        return {**_DISABLED, "shipments": []}
    return {"enabled": True, "shipments": svc.list_all()}


@router.post("", status_code=201)
def create_shipment(body: ShipmentCreate):
    if not DB_ENABLED:
        raise HTTPException(503, "shipments need a database (set DATABASE_URL)")
    try:
        return svc.create(body.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/{ref}")
def get_shipment(ref: str):
    if not DB_ENABLED:
        return {**_DISABLED, "shipment": None}
    out = svc.get(ref)
    if out is None:
        raise HTTPException(404, f"no shipment {ref!r}")
    return {"enabled": True, **out}


@router.patch("/{ref}")
def patch_shipment(ref: str, body: ShipmentPatch):
    if not DB_ENABLED:
        raise HTTPException(503, "shipments need a database (set DATABASE_URL)")
    out = svc.update(ref, body.model_dump())
    if out is None:
        raise HTTPException(404, f"no shipment {ref!r}")
    return out


@router.delete("/{ref}", status_code=204)
def delete_shipment(ref: str):
    if not DB_ENABLED:
        raise HTTPException(503, "shipments need a database (set DATABASE_URL)")
    if not svc.delete(ref):
        raise HTTPException(404, f"no shipment {ref!r}")


@router.post("/{ref}/revalue")
def revalue_shipment(ref: str):
    if not DB_ENABLED:
        raise HTTPException(503, "shipments need a database (set DATABASE_URL)")
    from sqlalchemy import select

    from ..db import session_scope
    from ..db.models import Shipment

    with session_scope() as s:
        row = s.scalars(select(Shipment).where(Shipment.ref == ref)).first()
        if row is None:
            raise HTTPException(404, f"no shipment {ref!r}")
        detached = Shipment(**{c.name: getattr(row, c.name) for c in Shipment.__table__.columns})
    try:
        return svc.revalue(detached, persist=True)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

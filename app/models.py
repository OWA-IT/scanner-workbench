from __future__ import annotations

import json
from datetime import datetime

from .extensions import db


class Location(db.Model):
    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    external_location_id = db.Column(db.String(64), nullable=False, unique=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    scans = db.relationship("Scan", back_populates="location", lazy=True)

    def __repr__(self) -> str:
        return f"<Location {self.name}>"


class Scan(db.Model):
    __tablename__ = "scans"

    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=False)
    barcode = db.Column(db.String(255), nullable=False)
    mode = db.Column(db.String(16), nullable=False)
    requested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    response_status = db.Column(db.String(32), nullable=False)
    response_code = db.Column(db.Integer)
    response_summary = db.Column(db.String(255), nullable=False)
    response_payload = db.Column(db.Text, nullable=False)
    error_detail = db.Column(db.Text)

    location = db.relationship("Location", back_populates="scans")

    @property
    def pretty_payload(self) -> str:
        if not self.response_payload:
            return ""

        try:
            parsed = json.loads(self.response_payload)
        except json.JSONDecodeError:
            return self.response_payload

        return json.dumps(parsed, indent=2, sort_keys=True)

    @property
    def result_state(self) -> str:
        if self.response_status in {"good", "bad"}:
            return self.response_status

        summary = (self.response_summary or "").strip().upper()
        if summary == "GOOD":
            return "good"
        if summary == "BAD":
            return "bad"
        return "neutral"

    @property
    def result_label(self) -> str:
        if self.response_summary:
            return self.response_summary
        return self.response_status.replace("_", " ").title()

    def __repr__(self) -> str:
        return f"<Scan {self.id} {self.barcode}>"

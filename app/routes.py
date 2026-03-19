from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from .api_client import dump_payload, validate_scan
from .extensions import db
from .models import Location, Scan

main_bp = Blueprint("main", __name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@main_bp.route("/", methods=["GET", "POST"])
def index():
    current_location = _get_selected_location()
    selected_mode = "execute"
    selected_test_result = "good"
    barcode = ""
    last_scan = Scan.query.order_by(Scan.requested_at.desc()).first()
    testing_mode = current_app.config.get("SCANNER_TESTING", False)

    if request.method == "POST":
        barcode = request.form.get("barcode", "").strip()
        selected_mode = "inquiry" if request.form.get("mode_inquiry") == "on" else "execute"
        selected_test_result = request.form.get("test_result", "good").lower()
        location = _get_selected_location()

        if not location or not location.active:
            flash("Choose an active location from Settings before validating.", "error")
        elif not barcode:
            flash("Enter a barcode before validating.", "error")
        else:
            result = validate_scan(
                location=location,
                barcode=barcode,
                mode=selected_mode,
                test_result=selected_test_result,
            )
            scan = Scan(
                location=location,
                barcode=barcode,
                mode=selected_mode,
                response_status=result["status"],
                response_code=result["http_status"],
                response_summary=result["summary"],
                response_payload=dump_payload(result["payload"]),
                error_detail=result.get("error_detail"),
            )
            db.session.add(scan)
            db.session.commit()
            last_scan = scan

    return render_template(
        "index.html",
        current_location=current_location,
        selected_mode=selected_mode,
        selected_test_result=selected_test_result,
        barcode=barcode,
        last_scan=last_scan,
        testing_mode=testing_mode,
    )


@main_bp.route("/history")
def history():
    scans = (
        Scan.query.order_by(Scan.requested_at.desc())
        .limit(50)
        .all()
    )
    return render_template("history.html", scans=scans)


@main_bp.route("/settings/location", methods=["POST"])
def set_location():
    location_id = request.form.get("location_id", type=int)
    next_url = request.form.get("next") or request.referrer or url_for("main.index")

    location = db.session.get(Location, location_id) if location_id else None
    if location is None or not location.active:
        flash("Choose a valid active location.", "error")
        return redirect(next_url)

    session["selected_location_id"] = location.id
    session.permanent = True
    flash(f"Location set to {location.name}.", "success")
    return redirect(next_url)


@admin_bp.route("/locations", methods=["GET", "POST"])
def locations():
    show_archived = request.args.get("show_archived") == "1"

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        external_location_id = request.form.get("external_location_id", "").strip()
        active = request.form.get("active") == "on"
        is_default = request.form.get("is_default") == "on"

        if not name or not external_location_id:
            flash("Name and external location ID are required.", "error")
        elif Location.query.filter_by(name=name).first():
            flash("A location with that name already exists.", "error")
        elif Location.query.filter_by(external_location_id=external_location_id).first():
            flash("That external location ID is already in use.", "error")
        else:
            if is_default:
                _clear_default_location()

            location = Location(
                name=name,
                external_location_id=external_location_id,
                active=active,
                is_default=is_default,
            )
            db.session.add(location)
            _ensure_default_location()
            db.session.commit()
            flash("Location created.", "success")
            return redirect(_locations_url(show_archived))

    locations_query = Location.query
    if not show_archived:
        locations_query = locations_query.filter_by(active=True)

    return render_template(
        "admin/locations.html",
        locations=locations_query.order_by(Location.active.desc(), Location.name.asc()).all(),
        show_archived=show_archived,
    )


@admin_bp.route("/locations/<int:location_id>/edit", methods=["GET", "POST"])
def edit_location(location_id: int):
    show_archived = _show_archived_requested()
    location = db.session.get(Location, location_id)
    if location is None:
        flash("Location not found.", "error")
        return redirect(_locations_url(show_archived))

    if request.method == "GET":
        return redirect(_locations_url(show_archived))

    name = request.form.get("name", "").strip()
    external_location_id = request.form.get("external_location_id", "").strip()
    active = request.form.get("active") == "on"
    is_default = request.form.get("is_default") == "on" and active

    if not name or not external_location_id:
        flash("Name and external location ID are required.", "error")
    else:
        duplicate_name = (
            Location.query.filter(Location.name == name, Location.id != location.id).first()
        )
        duplicate_external_id = (
            Location.query.filter(
                Location.external_location_id == external_location_id,
                Location.id != location.id,
            ).first()
        )

        if duplicate_name:
            flash("A location with that name already exists.", "error")
        elif duplicate_external_id:
            flash("That external location ID is already in use.", "error")
        else:
            if is_default:
                _clear_default_location(exclude_id=location.id)

            location.name = name
            location.external_location_id = external_location_id
            location.active = active
            location.is_default = is_default
            _ensure_default_location()
            db.session.commit()
            flash("Location updated.", "success")

    return redirect(_locations_url(show_archived))


@admin_bp.route("/locations/<int:location_id>/archive", methods=["POST"])
def archive_location(location_id: int):
    show_archived = _show_archived_requested()
    location = db.session.get(Location, location_id)
    if location is None:
        flash("Location not found.", "error")
        return redirect(_locations_url(show_archived))

    if location.active:
        location.active = False
        location.is_default = False
        _ensure_default_location()
        db.session.commit()
        flash("Location archived.", "success")
    else:
        location.active = True
        _ensure_default_location()
        db.session.commit()
        flash("Location restored.", "success")

    return redirect(_locations_url(show_archived))


def _active_locations() -> list[Location]:
    return Location.query.filter_by(active=True).order_by(Location.name.asc()).all()


def _get_selected_location() -> Location | None:
    active_locations = _active_locations()
    if not active_locations:
        session.pop("selected_location_id", None)
        return None

    selected_id = session.get("selected_location_id")
    if selected_id is not None:
        selected_location = db.session.get(Location, selected_id)
        if selected_location and selected_location.active:
            return selected_location

    default_id = _default_location_id(active_locations)
    if default_id is None:
        return None

    session["selected_location_id"] = default_id
    session.permanent = True
    return db.session.get(Location, default_id)


def _default_location_id(locations: list[Location]) -> int | None:
    for location in locations:
        if location.is_default:
            return location.id

    return locations[0].id if locations else None


def _clear_default_location(exclude_id: int | None = None) -> None:
    query = Location.query.filter_by(is_default=True)
    if exclude_id is not None:
        query = query.filter(Location.id != exclude_id)

    for location in query.all():
        location.is_default = False


def _ensure_default_location() -> None:
    active_default = Location.query.filter_by(active=True, is_default=True).first()
    if active_default:
        return

    fallback_location = Location.query.filter_by(active=True).order_by(Location.name.asc()).first()
    if fallback_location:
        fallback_location.is_default = True


def inject_settings_context() -> dict:
    return {
        "settings_locations": _active_locations(),
        "settings_location": _get_selected_location(),
    }


def _show_archived_requested() -> bool:
    return request.values.get("show_archived") == "1"


def _locations_url(show_archived: bool) -> str:
    if show_archived:
        return url_for("admin.locations", show_archived=1)
    return url_for("admin.locations")

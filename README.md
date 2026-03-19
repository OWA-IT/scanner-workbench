# Ticket Validation App

Minimal Flask app for an internal ticket validation workflow.

## Features

- Current-location setting stored in a signed session cookie
- Ticket validation form with `execute` and `inquiry` modes
- Result display for the most recent scan
- SQLite-backed scan history
- Admin location management with archive and restore support

## Run locally

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app run.py --debug run
```

## Environment variables

- `FLASK_SECRET_KEY`: Flask session secret
- `SCANNER_API_URL`: Endpoint used for the validation call
- `SCANNER_API_TIMEOUT`: Request timeout in seconds. Defaults to `10`
- `SCANNER_TESTING`: When `true`, disables live API calls and shows a Good/Bad test toggle in the UI

## Notes

- The main app is intentionally open. Admin routes are also open in this scaffold and should be protected once authentication is added.
- The app seeds one default location on first boot: `Main Warehouse / WHSE-001`.
- The app uses SQLite by default and creates `scanner.db` automatically. `DATABASE_URL` is still supported if you want to override the database connection.
- Database setup currently uses `db.create_all()` for simplicity. Move to migrations before shared deployment.
- The SOAP request currently sends `inquiry` and `scan` based on the contract you provided. Location is still stored locally and available for future endpoint needs.

# Scanner Validation App

Minimal Flask scaffold for an internal barcode validation workflow.

## Features

- Location selector with active/default location support
- Barcode validation form with `execute` and `inquiry` modes
- Result display for the most recent scan
- SQLite-backed scan history
- Admin location management module

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
- `DATABASE_URL`: SQLAlchemy database URI. Defaults to `sqlite:///scanner.db`
- `SCANNER_API_URL`: Endpoint used for the validation call
- `SCANNER_API_SOAP_ACTION`: Optional SOAPAction header if your service requires one
- `SCANNER_API_TIMEOUT`: Request timeout in seconds. Defaults to `10`
- `SCANNER_TESTING`: When `true`, disables live API calls and shows a Good/Bad test toggle in the UI

## Notes

- The main app is intentionally open. Admin routes are also open in this scaffold and should be protected once authentication is added.
- The app seeds one default location on first boot: `Main Warehouse / WHSE-001`.
- Database setup currently uses `db.create_all()` for simplicity. Move to migrations before shared deployment.
- The SOAP request currently sends `inquiry` and `scan` based on the contract you provided. Location is still stored locally and available for future endpoint needs.

# Airport Runway Scheduling System (Full Stack)

A Flask + SQLite web version of the uploaded C++ Airport Runway Scheduling project.

## Features
- Dashboard to register aircraft and view the waiting queue.
- Three runways with available/occupied status, manual busy marking and release.
- Priority scheduling using the same comparison order as the original C++ source:
  1. Lower priority number first (1 is highest).
  2. Lower fuel percentage first.
  3. Longer waiting time first.
  4. Aircraft ID alphabetically.
- Merge Sort implementation for queue ordering.
- Binary Search Tree rebuilt from waiting aircraft IDs, with inorder/preorder/postorder traversal and BST lookup.
- SQLite persistence: queue, runway state and assignment history remain after restarting the app.
- Search endpoint for waiting aircraft.

## Requirements
- Python 3.9 or newer
- pip

## Run on Windows
1. Extract the ZIP.
2. Open Command Prompt or VS Code terminal inside the `AirportRunwayFullStack` folder.
3. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Start the website:
   ```bash
   python app.py
   ```
6. Open `http://127.0.0.1:5000` in your browser.

## Run on macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Then open `http://127.0.0.1:5000`.

## Project structure
```text
AirportRunwayFullStack/
├── app.py                 # Flask backend, routes, algorithms
├── airport.db             # Created automatically on first run
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   └── tools.html
└── static/
    └── style.css
```

## Database tables
- `aircraft`: waiting aircraft details.
- `runways`: runway availability for R1, R2 and R3.
- `assignments`: history of aircraft assigned to runways.

## Notes
- This is an educational simulation, not certified air traffic control software.
- `airport.db` is created automatically beside `app.py`.
- The app runs in Flask debug mode for local development. Do not expose it publicly as-is.
- The secret key in `app.py` should be changed before any deployment.
- The web implementation re-creates the Merge Sort and BST behavior in Python. The original C++ file is not required to run this website.

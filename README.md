# VahanaShare — Bike and Vehicle Sharing System

A beginner-friendly full-stack vehicle sharing project based on the uploaded project abstract. It includes a responsive frontend, Flask REST API, and SQLite database.

## Features
- User registration, login and logout (passwords are hashed)
- Browse bikes, scooters and cars; search and filter listings
- Date-based booking with overlapping-booking checks and price calculation
- Booking history and booking notifications
- Admin dashboard with user/vehicle/booking totals and booking value
- Admin can add/remove vehicle listings and cancel bookings
- Responsive design for mobile and desktop

## Requirements
- Python 3.9 or newer
- Visual Studio Code (recommended)
- Internet connection for the optional Google Fonts import; the app itself works without it

## Run locally

1. Download or clone this repository and open the `vahanashare` folder in VS Code.
2. Open the VS Code terminal in this folder.
3. Create and activate a virtual environment:

   **Windows PowerShell**
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   **macOS / Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Install the dependency:
   ```bash
   pip install -r requirements.txt
   ```
5. Start the application:
   ```bash
   python app.py
   ```
6. Open **http://127.0.0.1:5000** in your browser.

The SQLite database is created automatically the first time the app starts. Sample vehicles are inserted automatically.

## Demo administrator account
- Email: `admin@vahanashare.com`
- Password: `Admin123!`

Use this account to open **My account → Admin**. Change the demo password and set a strong `SECRET_KEY` before deploying publicly. This is a student-project starter, not a production-ready rental/payment service.

## Push to GitHub
Create an empty repository on GitHub. In the VS Code terminal, run:

```bash
git init
git add .
git commit -m "Initial VahanaShare full-stack project"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Replace the URL with your own GitHub repository URL. Do not upload the generated database file or secrets.

## Project structure

```text
vahanashare/
├── app.py                 # Flask backend and REST API
├── requirements.txt       # Python dependencies
├── README.md              # Setup and GitHub instructions
├── .gitignore
├── templates/
│   └── index.html         # Main frontend page
└── static/
    ├── style.css          # Responsive styling
    └── app.js             # Frontend logic and API calls
```

## Important notes
- This version supports vehicle discovery and booking records. It does not process real payments or verify driving licences/vehicle documents.
- For a real deployment, use HTTPS, a strong secret key, secure hosting, backups, proper admin account management and additional validation/rate limiting.

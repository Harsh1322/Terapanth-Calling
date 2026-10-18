# Sangam — Committee Contact Tracker

Next.js frontend with a Flask/PostgreSQL backend for committee contact assignments, configurable data-collection tasks, progress tracking, audit history and Excel export. SQLite is used by default for local development. Includes a Chrome/Edge extension to collect **visible** participant numbers from a WhatsApp Web group page.

## Important limitations
- WhatsApp Web does not provide an official general-purpose API to export all group participants. The dashboard can open WhatsApp Web, but a normal web page cannot read WhatsApp’s private content in another tab; the companion extension is required to scan visible group members. It can miss participants or stop working when WhatsApp changes its interface. Open the group info/participant list and scroll through the members first. Always review the downloaded CSV.
- The extension does not bypass WhatsApp login, hidden data, privacy controls, or access restrictions. Use only with permission and in line with applicable law and WhatsApp terms.
- The dashboard provides the WhatsApp Web sign-in shortcut and scan/import instructions. The workflow is scan → download CSV → import through the authenticated admin dashboard. Direct extension-to-app posting is intentionally not enabled.
- Sign-in currently accepts a registered mobile number without verifying a password. Mobile number alone is not secure authentication; add OTP verification or another verified authentication method before production use.
- This initial scaffold should be tested and security-reviewed before production use.

## Local setup
1. Python 3.11+ recommended.
2. `python -m venv .venv` then activate it.
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and set a long random `SECRET_KEY`; optionally configure PostgreSQL `DATABASE_URL`.
5. `flask --app app init-db` (creates missing tables and widens an existing PostgreSQL password column)
6. `flask --app app bootstrap-admin`
7. Start the Flask API in one terminal: `flask --app app run --debug`.
8. In a second terminal, run `cd frontend`, `npm install`, then `npm run dev`.
9. Open `http://localhost:3000` for the Next.js interface. It proxies `/api/*` requests to Flask at `http://127.0.0.1:5000`; set `FLASK_API_URL` if the backend is hosted elsewhere.

The admin uses the configured `ADMIN_MOBILE` (default `7338884040`). Set `ADMIN_INITIAL_PASSWORD` to store an initial password for future authentication changes; the current sign-in flow only checks for an active account with the submitted mobile number. The Flask SQLAlchemy models retain the existing `tracker_user`, `tracker_contact`, and `tracker_auditlog` table names so existing Django-created records remain accessible. New data-task and submission tables are created by `flask --app app init-db`.

## Data collection tasks and call guide
- Admins can create and edit tasks, configure task-specific required/optional fields to match the shared Excel sheet, assign each task to selected active committee members, and disable or re-enable tasks. Disabling a task preserves its submissions.
- Age and area are collected for every task. Age **over 21** is classified as a **TYP member**. Otherwise, Ayanavaram, Kilpauk, Vepery, Puraswalkam, North Town, or ICF is classified as a **Kilpauk member**. If both rules match, TYP takes priority. If neither matches, the call is marked **Success** and the caller completes the task’s configured data fields.
- Committee members can open **Data tasks**, choose one of their assigned contacts, record age, area and task-specific details, and save the result. Collected fields are included in the Excel export’s **Data Collection** sheet.
- Member removal disables sign-in while retaining historical assignments and audit history. Name and mobile number can be edited in the Committee screen.
- While an authenticated workspace page is open, the frontend requests `/api/health` every five minutes and shows backend connectivity. This browser heartbeat stops when the page/browser closes; it cannot keep a sleeping service awake when no one visits. Use a hosting health check or uptime monitor for that requirement. The Render Blueprint uses a paid Starter backend service.

## Browser extension install (Chrome/Edge)
1. Open `chrome://extensions` (or `edge://extensions`).
2. Enable Developer mode.
3. Choose **Load unpacked** and select the `whatsapp-extension` directory.
4. Click **Open WhatsApp Web**, then sign in to your own WhatsApp account.
5. Open the group you want to import, open its participant list, and scroll through the list.
6. Click the extension, optionally label the group, scan visible participants, then download CSV.
7. Sign in to the tracker as admin and upload that CSV.

## Deploy to Render
1. Create a new empty GitHub repository and push this project.
2. In Render, create a Blueprint from the repository and review the PostgreSQL/web service plans and current pricing. The Blueprint creates separate Flask and Next.js services.
3. Set `ADMIN_MOBILE` to the number that will use administrator access; the default is `7338884040`.
4. The frontend service proxies requests to the Flask service using `FLASK_API_URL`; update that value if the Flask service URL changes.
5. Deploy; the Flask startup command creates any missing tables and initializes the admin account.
6. Open the Next.js service URL and sign in with the registered mobile number. Never commit `.env` or secrets.

## CSV/XLSX columns
Recognized phone columns include `phone`, `mobile`, `mobile number`, `phone number`, `number`, `telephone`; names can be `name`, `full name`, `contact name`. Optional `group` / `group name` is retained. Phone numbers are normalized and duplicate phone numbers skipped.

## Contact outcomes
- Pending
- TYP member
- Kilpauk member
- Success → Chennai / Kilpauk / TYP / Other (data collected)
- Call didn't pick up
- Number invalid
- Need to follow up

## Before production
Add database migration tooling for future schema changes, rate-limit login, implement verified authentication, add backup/restore and error monitoring, and test contact-import edge cases. Use a secure admin password and HTTPS.

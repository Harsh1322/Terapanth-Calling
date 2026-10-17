# Committee Contact Tracker

Django/PostgreSQL app for committee contact assignments, status tracking, audit history and Excel export. Includes an experimental Chrome/Edge extension to collect **visible** participant numbers from a WhatsApp Web group page.

## Important limitations
- WhatsApp Web does not provide an official general-purpose API to export all group participants. The extension scans visible DOM elements and can miss participants or stop working when WhatsApp changes its interface. Open the group info/participant list and scroll through the members first. Always review the downloaded CSV.
- The extension does not bypass WhatsApp login, hidden data, privacy controls, or access restrictions. Use only with permission and in line with applicable law and WhatsApp terms.
- Current extension workflow is scan → download CSV → import through the authenticated admin dashboard. Direct extension-to-app posting is intentionally not enabled.
- Mobile number alone is an identifier, not secure authentication. This app uses mobile number + password. If you later require passwordless login, use OTP verification rather than trusting a typed number.
- This initial scaffold should be tested and security-reviewed before production use.

## Local setup
1. Python 3.11+ recommended.
2. `python -m venv .venv` then activate it.
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`, set `SECRET_KEY`; optionally configure PostgreSQL `DATABASE_URL`.
5. `python manage.py makemigrations tracker`
6. `python manage.py migrate`
7. `python manage.py bootstrap_admin`
8. `python manage.py runserver`

The first admin uses the configured `ADMIN_MOBILE` (default `7338884040`). Every active account signs in with its registered mobile number only.

## Browser extension install (Chrome/Edge)
1. Open `chrome://extensions` (or `edge://extensions`).
2. Enable Developer mode.
3. Choose **Load unpacked** and select the `whatsapp-extension` directory.
4. Click **Open WhatsApp Web**, then sign in to your own WhatsApp account.
5. Open the group you want to import, open its participant list, and scroll through the list.
6. Click the extension, optionally label the group, scan visible participants, then download CSV.
6. Sign in to the tracker as admin and upload that CSV.

## Deploy to Render
1. Create a new empty GitHub repository and push this project.
2. In Render, create a Blueprint from the repository and review the PostgreSQL/web service plans and current pricing.
3. Set `ADMIN_MOBILE` to the number that will use administrator access; the default is `7338884040`.
4. Deploy; the startup command runs migrations and initializes the admin account.
5. Open the Render URL and sign in with that mobile number. Never commit `.env` or secrets.

## CSV/XLSX columns
Recognized phone columns include `phone`, `mobile`, `mobile number`, `phone number`, `number`, `telephone`; names can be `name`, `full name`, `contact name`. Optional `group` / `group name` is retained. Phone numbers are normalized and duplicate phone numbers skipped.

## Contact outcomes
- Pending
- Success → Chennai / Kilpauk / TYP
- Call didn't pick up
- Number invalid
- Need to follow up

## Before production
Generate and commit migrations, add automated tests, rate-limit login, enforce password rotation, add backup/restore and error monitoring, and test contact-import edge cases. Use a secure admin password and HTTPS.

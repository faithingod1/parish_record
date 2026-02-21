# Local Church Confirmation Record Management System

## 1) System Architecture

This project is a **single-machine local web app** for managing church confirmation records.

- **FastAPI** handles routing, validation flow, and server-side rendering.
- **Jinja2 templates** render pages (login, dashboard, CRUD pages) for non-technical staff.
- **SQLite** stores all data in one local file (`church_records.db`) for simple backup and portability.
- **SQLAlchemy ORM** provides safe database access and helps prevent SQL injection.
- **SessionMiddleware** stores authenticated user sessions securely via signed cookies.
- **bcrypt** secures admin passwords.
- **CSRF token checks** protect form submissions.

### Request Flow
1. User opens app on `http://127.0.0.1:8000`.
2. User logs in via `/login`.
3. Session cookie is created and checked on protected routes.
4. CRUD/search/export actions use SQLAlchemy queries.
5. Templates display results in a clean interface.

---

## 2) Folder Structure

```text
parish_record/
├── auth.py
├── database.py
├── main.py
├── models.py
├── requirements.txt
├── church_records.db          # auto-generated after first run
├── static/
│   └── styles.css
└── templates/
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── confirmations_list.html
    ├── confirmation_form.html
    └── confirmation_detail.html
```

---

## 3) Run & Setup on Windows

### Prerequisites
- Windows 10/11
- Python 3.10+ installed

### Installation Steps

1. Open **PowerShell** in the project folder.
2. Create virtual environment:
   ```powershell
   python -m venv .venv
   ```
3. Activate it:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Start app:
   ```powershell
   uvicorn main:app --reload
   ```
6. Open browser: `http://127.0.0.1:8000`

---

## 4) Example Admin Account Creation

On first visit to `/login`, the app auto-creates:
- **username:** `admin`
- **password:** `admin123`

You can also add users manually via a Python shell if needed.

---

## 5) Backup Instructions

After login, use sidebar buttons:

- **Backup DB**: downloads full SQLite file (`church_records_backup.db`)
- **Export CSV**: downloads confirmation data as CSV (`confirmations_export.csv`)

Store backups on USB/external drive regularly.

---

## 6) Security Notes

- Passwords are hashed with bcrypt.
- Session-based auth protects all private pages.
- CSRF token required for all POST forms.
- SQLAlchemy ORM + parameterized queries protect against SQL injection.
- Input is validated (required fields, date parsing).


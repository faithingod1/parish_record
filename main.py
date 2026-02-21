import csv
import io
import os
import secrets
from datetime import date, datetime

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from auth import hash_password, verify_password
from database import Base, engine, get_db
from models import Confirmation, User

app = FastAPI(title="Church Confirmation Record Management")
app.add_middleware(SessionMiddleware, secret_key="replace-this-in-production-with-strong-key")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)


# ---------- Security & session helpers ----------
def login_required(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})


def generate_csrf_token(request: Request) -> str:
    token = secrets.token_urlsafe(32)
    request.session["csrf_token"] = token
    return token


def validate_csrf(request: Request, csrf_token: str):
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")


# ---------- Utility ----------
def parse_date(value: str, field_name: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date format for {field_name}. Use YYYY-MM-DD") from exc


def ensure_admin_exists(db: Session):
    """Create a default admin account only if no users exist."""
    if db.query(User).count() == 0:
        default_user = User(username="admin", password_hash=hash_password("admin123"))
        db.add(default_user)
        db.commit()


# ---------- Authentication routes ----------
@app.get("/")
def root(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    ensure_admin_exists(db)
    csrf_token = generate_csrf_token(request)
    return templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token})


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)

    user = db.query(User).filter(User.username == username.strip()).first()
    if not user or not verify_password(password, user.password_hash):
        new_csrf = generate_csrf_token(request)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password", "csrf_token": new_csrf},
            status_code=400,
        )

    request.session["user_id"] = user.id
    request.session["username"] = user.username
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


# ---------- Dashboard ----------
@app.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db), _=Depends(login_required)):
    total_records = db.query(Confirmation).count()
    csrf_token = generate_csrf_token(request)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": request.session.get("username"),
            "total_records": total_records,
            "csrf_token": csrf_token,
        },
    )


# ---------- Confirmation CRUD ----------
@app.get("/confirmations")
def list_confirmations(
    request: Request,
    q: str = "",
    db: Session = Depends(get_db),
    _=Depends(login_required),
):
    query = db.query(Confirmation)

    if q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Confirmation.full_name.ilike(term),
                Confirmation.church_name.ilike(term),
                Confirmation.priest_name.ilike(term),
                func.strftime("%Y-%m-%d", Confirmation.confirmation_date).ilike(term),
            )
        )

    records = query.order_by(Confirmation.confirmation_date.desc()).all()
    csrf_token = generate_csrf_token(request)
    return templates.TemplateResponse(
        "confirmations_list.html",
        {"request": request, "records": records, "q": q, "csrf_token": csrf_token},
    )


@app.get("/confirmations/new")
def new_confirmation_form(request: Request, _=Depends(login_required)):
    csrf_token = generate_csrf_token(request)
    return templates.TemplateResponse(
        "confirmation_form.html",
        {"request": request, "mode": "create", "csrf_token": csrf_token},
    )


@app.post("/confirmations/new")
def create_confirmation(
    request: Request,
    full_name: str = Form(...),
    date_of_birth: str = Form(...),
    confirmation_date: str = Form(...),
    church_name: str = Form(...),
    priest_name: str = Form(...),
    sponsor_name: str = Form(""),
    remarks: str = Form(""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(login_required),
):
    validate_csrf(request, csrf_token)

    new_record = Confirmation(
        full_name=full_name.strip(),
        date_of_birth=parse_date(date_of_birth, "date_of_birth"),
        confirmation_date=parse_date(confirmation_date, "confirmation_date"),
        church_name=church_name.strip(),
        priest_name=priest_name.strip(),
        sponsor_name=sponsor_name.strip(),
        remarks=remarks.strip(),
    )

    db.add(new_record)
    db.commit()
    return RedirectResponse(url="/confirmations", status_code=303)


@app.get("/confirmations/{record_id}")
def view_confirmation(record_id: int, request: Request, db: Session = Depends(get_db), _=Depends(login_required)):
    record = db.get(Confirmation, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    csrf_token = generate_csrf_token(request)
    return templates.TemplateResponse(
        "confirmation_detail.html",
        {"request": request, "record": record, "csrf_token": csrf_token},
    )


@app.get("/confirmations/{record_id}/edit")
def edit_confirmation_form(record_id: int, request: Request, db: Session = Depends(get_db), _=Depends(login_required)):
    record = db.get(Confirmation, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    csrf_token = generate_csrf_token(request)
    return templates.TemplateResponse(
        "confirmation_form.html",
        {"request": request, "mode": "edit", "record": record, "csrf_token": csrf_token},
    )


@app.post("/confirmations/{record_id}/edit")
def update_confirmation(
    record_id: int,
    request: Request,
    full_name: str = Form(...),
    date_of_birth: str = Form(...),
    confirmation_date: str = Form(...),
    church_name: str = Form(...),
    priest_name: str = Form(...),
    sponsor_name: str = Form(""),
    remarks: str = Form(""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(login_required),
):
    validate_csrf(request, csrf_token)

    record = db.get(Confirmation, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    record.full_name = full_name.strip()
    record.date_of_birth = parse_date(date_of_birth, "date_of_birth")
    record.confirmation_date = parse_date(confirmation_date, "confirmation_date")
    record.church_name = church_name.strip()
    record.priest_name = priest_name.strip()
    record.sponsor_name = sponsor_name.strip()
    record.remarks = remarks.strip()

    db.commit()
    return RedirectResponse(url=f"/confirmations/{record_id}", status_code=303)


@app.post("/confirmations/{record_id}/delete")
def delete_confirmation(
    record_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(login_required),
):
    validate_csrf(request, csrf_token)

    record = db.get(Confirmation, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    db.delete(record)
    db.commit()
    return RedirectResponse(url="/confirmations", status_code=303)


# ---------- Backup / export ----------
@app.get("/backup/db")
def backup_db(request: Request, _=Depends(login_required)):
    db_path = "church_records.db"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found")

    with open(db_path, "rb") as file:
        data = file.read()

    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="church_records_backup.db"'},
    )


@app.get("/backup/csv")
def export_csv(request: Request, db: Session = Depends(get_db), _=Depends(login_required)):
    records = db.query(Confirmation).order_by(Confirmation.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "Full Name",
            "Date of Birth",
            "Confirmation Date",
            "Church Name",
            "Priest Name",
            "Sponsor Name",
            "Remarks",
            "Created At",
        ]
    )

    for record in records:
        writer.writerow(
            [
                record.id,
                record.full_name,
                record.date_of_birth,
                record.confirmation_date,
                record.church_name,
                record.priest_name,
                record.sponsor_name,
                record.remarks,
                record.created_at,
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="confirmations_export.csv"'},
    )

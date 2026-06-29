from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from jose import JWTError

from schemas import (
    UserRegister,
    UserLogin,
    ForgotPassword,
    ResetPassword,
    VerifyEmail
)

from models import create_users_table
from database import get_connection
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)
from email_service import send_otp_email

from datetime import datetime, timedelta
from dotenv import load_dotenv
from urllib.parse import urlencode
import random
import secrets
import httpx
import os

load_dotenv()

app = FastAPI(
    title="AuthAPI",
    description="Reusable Authentication API using FastAPI + MySQL + JWT + Google OAuth",
    version="1.0.0"
)

security = HTTPBearer()

# In-memory OAuth state store
oauth_states = {}

# ── Middleware ──
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "authapi_session_secret"),
    same_site="lax",
    https_only=False
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    create_users_table()


@app.get("/")
def home():
    return {
        "message": "Welcome to AuthAPI",
        "status": "Backend is running successfully"
    }


@app.post("/register")
def register(user: UserRegister):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (user.email,))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(user.password)

    otp = str(random.randint(100000, 999999))
    otp_expiry = datetime.now() + timedelta(minutes=10)

    cursor.execute(
        """
        INSERT INTO users
        (full_name, email, password, verification_otp, otp_expiry, is_verified)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            user.full_name,
            user.email,
            hashed_password,
            otp,
            otp_expiry,
            False
        )
    )

    connection.commit()
    cursor.close()
    connection.close()

    send_otp_email(user.email, otp, purpose="verify")

    return {
        "message": "User registered successfully. OTP sent to your email."
    }


@app.post("/verify-email")
def verify_email(data: VerifyEmail):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (data.email,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=404, detail="User not found")

    if user["is_verified"]:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=400, detail="Email already verified")

    if user["verification_otp"] != data.otp:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if user["otp_expiry"] < datetime.now():
        cursor.close()
        connection.close()
        raise HTTPException(status_code=400, detail="OTP expired")

    cursor.execute(
        """
        UPDATE users
        SET is_verified=%s,
            verification_otp=NULL,
            otp_expiry=NULL
        WHERE email=%s
        """,
        (True, data.email)
    )

    connection.commit()
    cursor.close()
    connection.close()

    return {
        "message": "Email verified successfully"
    }


@app.post("/login")
def login(user: UserLogin):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (user.email,))
    db_user = cursor.fetchone()

    cursor.close()
    connection.close()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not db_user["is_verified"]:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before login"
        )

    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid password")

    access_token = create_access_token(
        data={
            "user_id": db_user["id"],
            "email": db_user["email"],
            "role": db_user["role"]
        }
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer"
    }


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id = payload.get("user_id")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, full_name, email, role, is_verified FROM users WHERE id=%s",
            (user_id,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.get("/profile")
def profile(current_user: dict = Depends(get_current_user)):
    return {
        "message": "Profile fetched successfully",
        "user": current_user
    }


@app.get("/admin-only")
def admin_only(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied. Admin only."
        )

    return {
        "message": "Welcome Admin!",
        "user": current_user
    }


@app.post("/logout")
def logout():
    return {
        "message": "Logout successful. Please remove token from frontend/localStorage."
    }


@app.post("/forgot-password")
def forgot_password(user: ForgotPassword):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (user.email,))
    db_user = cursor.fetchone()

    if not db_user:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=404, detail="Email not found")

    reset_token = str(random.randint(100000, 999999))
    expiry = datetime.now() + timedelta(minutes=15)

    cursor.execute(
        """
        UPDATE users
        SET reset_token=%s,
            reset_token_expiry=%s
        WHERE email=%s
        """,
        (reset_token, expiry, user.email)
    )

    connection.commit()
    cursor.close()
    connection.close()

    send_otp_email(user.email, reset_token, purpose="reset")

    return {
        "message": "Password reset OTP sent to your email."
    }


@app.post("/reset-password")
def reset_password(data: ResetPassword):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE reset_token=%s", (data.token,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=400, detail="Invalid reset token")

    if user["reset_token_expiry"] < datetime.now():
        cursor.close()
        connection.close()
        raise HTTPException(status_code=400, detail="Reset token expired")

    hashed_password = hash_password(data.new_password)

    cursor.execute(
        """
        UPDATE users
        SET password=%s,
            reset_token=NULL,
            reset_token_expiry=NULL
        WHERE id=%s
        """,
        (hashed_password, user["id"])
    )

    connection.commit()
    cursor.close()
    connection.close()

    return {
        "message": "Password updated successfully"
    }


@app.get("/auth/google/login")
async def google_login():
    state = secrets.token_urlsafe(32)
    oauth_states[state] = True

    params = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }

    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=url)


@app.get("/auth/google/callback")
async def google_callback(request: Request):
    state = request.query_params.get("state")
    code  = request.query_params.get("code")

    if not state or state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    del oauth_states[state]

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
                "grant_type": "authorization_code",
            }
        )
        token_data = token_response.json()

    # Get user info from Google
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
        user_info = user_response.json()

    email     = user_info.get("email")
    full_name = user_info.get("name")

    if not email:
        raise HTTPException(status_code=400, detail="Google login failed")

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    db_user = cursor.fetchone()

    if not db_user:
        cursor.execute(
            """
            INSERT INTO users (full_name, email, password, role, is_verified)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (full_name, email, "GOOGLE_AUTH_USER", "User", True)
        )
        connection.commit()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        db_user = cursor.fetchone()

    access_token = create_access_token(
        data={
            "user_id": db_user["id"],
            "email":   db_user["email"],
            "role":    db_user["role"]
        }
    )

    cursor.close()
    connection.close()

    frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")
    return RedirectResponse(
        url=f"{frontend_url}/dashboard.html?{urlencode({'token': access_token})}"
    )
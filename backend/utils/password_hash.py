# AuthAPI

AuthAPI is a reusable authentication system built with **FastAPI**, **MySQL**, **JWT**, and **HTML/CSS/JavaScript**. It is designed to provide a secure and ready-to-integrate authentication module that can be reused across future web applications, eliminating the need to implement authentication from scratch for every project.

## Features

* User Registration and Login
* JWT Authentication
* Password Hashing (bcrypt)
* Email Verification (OTP)
* Forgot Password & Reset Password
* Google OAuth Login
* Protected Routes
* Role-Based Authorization
* Interactive API Documentation (Swagger)

## Tech Stack

**Backend:** FastAPI, Python, MySQL, SQLAlchemy, Pydantic, Passlib, JWT, Authlib

**Frontend:** HTML, CSS, JavaScript

## Project Structure

```text
AuthAPI/
│
├── backend/
│   ├── routers/
│   ├── utils/
│   ├── auth.py
│   ├── database.py
│   ├── email_service.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── requirements.txt
│
├── frontend/
│   ├── dashboard.html
│   ├── forgot-password.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── reset-password.html
│   ├── verify-email.html
│   ├── script.js
│   └── style.css
│
├── .gitignore
└── README.md
```

## Installation

```bash
git clone https://github.com/madhwanibhumika24/AuthAPI.git

cd AuthAPI/backend

pip install -r requirements.txt

uvicorn main:app --reload
```

The API will be available at:

```
http://127.0.0.1:8000
```

Swagger Documentation:

```
http://127.0.0.1:8000/docs
```

## Project Goal

The objective of AuthAPI is to provide a modular and reusable authentication service that can be integrated into future applications with minimal configuration. It serves as a centralized authentication solution supporting secure user management, authorization, and modern authentication workflows.

## Future Enhancements

* Refresh Token Authentication
* Resend OTP
* Profile Management
* Profile Image Upload
* Docker Support
* Deployment (Render & Vercel)
* Two-Factor Authentication
* Login History and Session Management

## Author

**Bhumika Madhwani**

MCA Student | Aspiring Backend & AI Developer

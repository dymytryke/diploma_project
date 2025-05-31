import asyncio

from cmp_core.api.v1.audit import router as audit_router
from cmp_core.api.v1.auth import router as auth_router
from cmp_core.api.v1.azure import router as azure_vm_router
from cmp_core.api.v1.ec2 import router as ec2_router
from cmp_core.api.v1.members import router as members_router
from cmp_core.api.v1.projects import router as projects_router
from cmp_core.api.v1.users import router as users_router
from cmp_core.core.config import settings
from cmp_core.core.db import get_db
from cmp_core.models.role import RoleName
from cmp_core.models.user import User
from cmp_core.services.auth import hash_password
from fastapi import APIRouter, FastAPI  # Import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

app = FastAPI(title="CMP")

origins = settings.cors_origins or [
    "http://localhost:5137",  # Ensure this matches your frontend dev port if needed
    "http://localhost",  # For access via Nginx ingress
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(members_router)
api_v1_router.include_router(ec2_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(azure_vm_router)

# Register the main /api/v1 router with the app
app.include_router(api_v1_router)


@app.on_event("startup")
async def ensure_initial_admin():
    # якщо в ENV задані облікові дані для адміна
    email = settings.initial_admin_email
    pwd = settings.initial_admin_password
    if not email or not pwd:
        return

    # чекати, доки БД підніметься
    await asyncio.sleep(1)

    # перевіряємо, чи є хоча б один Admin
    async for db in get_db():
        q = await db.execute(select(User).where(User.role_id == RoleName.admin))
        admin = q.scalars().first()
        if admin:
            return  # є адмін – нічого не робимо

        # перевіряємо, чи користувач із цим email існує
        q2 = await db.execute(select(User).where(User.email == email))
        existing = q2.scalars().first()

        if existing:
            existing.role_id = RoleName.admin
            await db.commit()
        else:
            # створюємо нового із роллю admin
            user = User(
                email=email,
                password_hash=hash_password(pwd),
                role_id=RoleName.admin,
            )
            db.add(user)
            await db.commit()
        return

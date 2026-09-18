from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.modules import MODULE_REGISTRY
from app.core.security import create_access_token, hash_password, verify_password
from app.models.organization import ModuleEnablement, Organization
from app.models.user import RoleEnum, User
from app.schemas.auth import LoginResponse, RegisterRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.admin_email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    org = Organization(**payload.organization.model_dump())
    db.add(org)
    db.flush()  # assign org.id without committing yet

    # New organizations start with every module enabled at signup; the admin
    # can turn individual modules off from the onboarding/settings screen.
    for module in MODULE_REGISTRY:
        db.add(ModuleEnablement(organization_id=org.id, module_key=module.key, enabled=True))

    admin = User(
        organization_id=org.id,
        email=payload.admin_email,
        hashed_password=hash_password(payload.admin_password),
        full_name=payload.admin_full_name,
        role=RoleEnum.org_admin,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@router.post("/login", response_model=LoginResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role.value})
    return LoginResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

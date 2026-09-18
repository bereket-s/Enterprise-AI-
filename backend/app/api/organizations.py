from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_org_id, get_current_user, require_roles
from app.core.modules import MODULE_REGISTRY, is_valid_module
from app.core.security import hash_password
from app.models.organization import ModuleEnablement, Organization
from app.models.user import RoleEnum, User
from app.schemas.auth import UserCreate, UserOut
from app.schemas.organization import ModuleStatus, ModuleToggleRequest, OrganizationOut

router = APIRouter(prefix="/api/org", tags=["organization"])


@router.get("/me", response_model=OrganizationOut)
def get_my_organization(org_id: int = Depends(current_org_id), db: Session = Depends(get_db)):
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    return org


@router.get("/modules", response_model=list[ModuleStatus])
def list_modules(org_id: int = Depends(current_org_id), db: Session = Depends(get_db)):
    enablements = {
        e.module_key: e.enabled
        for e in db.query(ModuleEnablement).filter(ModuleEnablement.organization_id == org_id)
    }
    return [
        ModuleStatus(
            key=m.key,
            name=m.name,
            description=m.description,
            maturity=m.maturity,
            enabled=enablements.get(m.key, False),
        )
        for m in MODULE_REGISTRY
    ]


@router.put("/modules/{module_key}", response_model=ModuleStatus)
def toggle_module(
    module_key: str,
    payload: ModuleToggleRequest,
    org_id: int = Depends(current_org_id),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
):
    if not is_valid_module(module_key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown module '{module_key}'")

    enablement = (
        db.query(ModuleEnablement)
        .filter(ModuleEnablement.organization_id == org_id, ModuleEnablement.module_key == module_key)
        .first()
    )
    if enablement is None:
        enablement = ModuleEnablement(organization_id=org_id, module_key=module_key)
        db.add(enablement)
    enablement.enabled = payload.enabled
    db.commit()

    module_def = next(m for m in MODULE_REGISTRY if m.key == module_key)
    return ModuleStatus(
        key=module_def.key,
        name=module_def.name,
        description=module_def.description,
        maturity=module_def.maturity,
        enabled=enablement.enabled,
    )


@router.get("/users", response_model=list[UserOut])
def list_users(
    org_id: int = Depends(current_org_id),
    db: Session = Depends(get_db),
    _manager: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.manager, RoleEnum.super_admin)),
):
    return db.query(User).filter(User.organization_id == org_id).all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    org_id: int = Depends(current_org_id),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    user = User(
        organization_id=org_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        department=payload.department,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

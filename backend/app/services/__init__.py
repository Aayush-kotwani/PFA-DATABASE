"""Business logic services package."""

from app.services.area_service import (
    create_area,
    deactivate_area,
    get_area,
    list_areas,
    update_area,
)
from app.services.audit_service import log_audit
from app.services.auth_service import authenticate_user
from app.services.case_service import (
    create_case,
    get_case,
    list_cases,
    soft_delete_case,
    update_case,
)
from app.services.dog_service import (
    create_dog,
    delete_dog,
    get_dog,
    list_dogs,
    update_dog,
)
from app.services.photo_service import (
    list_photos,
    soft_delete_photo,
    update_photo,
    upload_photo,
)
from app.services.public_service import generate_dog_qr_png, get_public_dog_info
from app.services.user_service import (
    create_user,
    list_users,
    reset_user_password,
    update_user,
)
from app.services.vaccination_service import (
    create_vaccination,
    get_due_vaccinations,
    get_vaccination,
    list_vaccinations,
    soft_delete_vaccination,
    update_vaccination,
)

__all__ = [
    "authenticate_user",
    "log_audit",
    "list_users",
    "create_user",
    "update_user",
    "reset_user_password",
    "list_areas",
    "get_area",
    "create_area",
    "update_area",
    "deactivate_area",
    "list_dogs",
    "get_dog",
    "create_dog",
    "update_dog",
    "delete_dog",
    "list_cases",
    "get_case",
    "create_case",
    "update_case",
    "soft_delete_case",
    "list_vaccinations",
    "get_vaccination",
    "create_vaccination",
    "update_vaccination",
    "soft_delete_vaccination",
    "get_due_vaccinations",
    "list_photos",
    "upload_photo",
    "update_photo",
    "soft_delete_photo",
    "generate_dog_qr_png",
    "get_public_dog_info",
]

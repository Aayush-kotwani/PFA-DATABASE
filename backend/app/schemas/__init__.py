"""Validation and serialization schemas package."""

from app.schemas.area import (
    AreaCreateInSchema,
    AreaListOutSchema,
    AreaListQuerySchema,
    AreaOutSchema,
    AreaUpdateInSchema,
)
from app.schemas.auth import LoginInSchema, LoginOutSchema, UserMeOutSchema
from app.schemas.case import (
    CaseCreateInSchema,
    CaseListOutSchema,
    CaseMessageOutSchema,
    CaseOutSchema,
    CaseUpdateInSchema,
)
from app.schemas.dog import (
    DogAreaSummarySchema,
    DogCreateInSchema,
    DogListOutSchema,
    DogListQuerySchema,
    DogMessageOutSchema,
    DogOutSchema,
    DogUpdateInSchema,
)
from app.schemas.user import (
    UserCreateInSchema,
    UserListOutSchema,
    UserMessageOutSchema,
    UserOutSchema,
    UserResetPasswordInSchema,
    UserUpdateInSchema,
)
from app.schemas.vaccination import (
    DueVaccinationItemSchema,
    DueVaccinationQuerySchema,
    DueVaccinationsOutSchema,
    VaccinationCreateInSchema,
    VaccinationListOutSchema,
    VaccinationMessageOutSchema,
    VaccinationOutSchema,
    VaccinationUpdateInSchema,
)

__all__ = [
    "LoginInSchema",
    "LoginOutSchema",
    "UserMeOutSchema",
    "UserOutSchema",
    "UserListOutSchema",
    "UserCreateInSchema",
    "UserUpdateInSchema",
    "UserResetPasswordInSchema",
    "UserMessageOutSchema",
    "AreaOutSchema",
    "AreaListQuerySchema",
    "AreaListOutSchema",
    "AreaCreateInSchema",
    "AreaUpdateInSchema",
    "DogAreaSummarySchema",
    "DogOutSchema",
    "DogListQuerySchema",
    "DogListOutSchema",
    "DogCreateInSchema",
    "DogUpdateInSchema",
    "DogMessageOutSchema",
    "CaseOutSchema",
    "CaseListOutSchema",
    "CaseCreateInSchema",
    "CaseUpdateInSchema",
    "CaseMessageOutSchema",
    "VaccinationOutSchema",
    "VaccinationListOutSchema",
    "VaccinationCreateInSchema",
    "VaccinationUpdateInSchema",
    "VaccinationMessageOutSchema",
    "DueVaccinationQuerySchema",
    "DueVaccinationItemSchema",
    "DueVaccinationsOutSchema",
]

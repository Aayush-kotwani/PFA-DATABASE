"""Validation and serialization schemas package."""

from app.schemas.area import (
    AreaCreateInSchema,
    AreaListOutSchema,
    AreaListQuerySchema,
    AreaOutSchema,
    AreaUpdateInSchema,
)
from app.schemas.audit_log import (
    AuditLogListOutSchema,
    AuditLogOutSchema,
    AuditLogQuerySchema,
)
from app.schemas.auth import LoginInSchema, LoginOutSchema, UserMeOutSchema
from app.schemas.case import (
    CaseCreateInSchema,
    CaseListOutSchema,
    CaseMessageOutSchema,
    CaseOutSchema,
    CaseUpdateInSchema,
)
from app.schemas.dashboard import (
    AreaDogCountSchema,
    DashboardStatsOutSchema,
    VaccinationDueCountsSchema,
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
from app.schemas.export import AnalyticsExportQuerySchema
from app.schemas.photo import (
    PhotoListOutSchema,
    PhotoMessageOutSchema,
    PhotoOutSchema,
    PhotoUpdateInSchema,
    PhotoUploadInSchema,
)
from app.schemas.public import PublicDogOutSchema, PublicVaccinationSchema
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
    "PhotoOutSchema",
    "PhotoListOutSchema",
    "PhotoUploadInSchema",
    "PhotoUpdateInSchema",
    "PhotoMessageOutSchema",
    "PublicVaccinationSchema",
    "PublicDogOutSchema",
    "AuditLogQuerySchema",
    "AuditLogOutSchema",
    "AuditLogListOutSchema",
    "AreaDogCountSchema",
    "VaccinationDueCountsSchema",
    "DashboardStatsOutSchema",
    "AnalyticsExportQuerySchema",
]

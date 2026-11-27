"""Dogs management API routes."""

from apiflask import APIBlueprint
from flask import Response

from app.schemas.dog import (
    DogCreateInSchema,
    DogListOutSchema,
    DogListQuerySchema,
    DogMessageOutSchema,
    DogOutSchema,
    DogUpdateInSchema,
)
from app.services import dog_service, public_service
from app.utils.auth import get_current_user, login_required, roles_required

dogs_bp = APIBlueprint("dogs", __name__, url_prefix="/api/dogs", tag="Dogs")


@dogs_bp.get("", strict_slashes=False)
@dogs_bp.input(DogListQuerySchema, location="query")
@dogs_bp.output(DogListOutSchema, status_code=200)
@dogs_bp.doc(
    summary="List dogs",
    description="Retrieve paginated list of non-deleted dogs with search and filters.",
    security="BearerAuth",
)
@login_required
def list_dogs(query_data):
    """Retrieve filtered, paginated dogs."""
    return dog_service.list_dogs(query_data)


@dogs_bp.get("/<int:dog_id>")
@dogs_bp.output(DogOutSchema, status_code=200)
@dogs_bp.doc(
    summary="Get dog details",
    description="Retrieve details for a single non-deleted dog by ID.",
    security="BearerAuth",
)
@login_required
def get_dog(dog_id):
    """Retrieve a single dog by ID."""
    return dog_service.get_dog(dog_id)


@dogs_bp.post("", strict_slashes=False)
@dogs_bp.input(DogCreateInSchema)
@dogs_bp.output(DogOutSchema, status_code=201)
@dogs_bp.doc(
    summary="Register a new dog",
    description="Create a new dog profile with auto-generated area dog_code.",
    security="BearerAuth",
)
@login_required
def create_dog(json_data):
    """Create a new dog."""
    current_user = get_current_user()
    return dog_service.create_dog(json_data, actor=current_user)


@dogs_bp.patch("/<int:dog_id>")
@dogs_bp.input(DogUpdateInSchema)
@dogs_bp.output(DogOutSchema, status_code=200)
@dogs_bp.doc(
    summary="Update dog details",
    description="Update dog profile fields. Volunteers' guardian_phone updates are ignored.",
    security="BearerAuth",
)
@login_required
def update_dog(dog_id, json_data):
    """Update an existing dog."""
    current_user = get_current_user()
    return dog_service.update_dog(dog_id, json_data, actor=current_user)


@dogs_bp.delete("/<int:dog_id>")
@dogs_bp.output(DogMessageOutSchema, status_code=200)
@dogs_bp.doc(
    summary="Soft-delete dog (Admin only)",
    description="Mark a dog record as soft-deleted.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def delete_dog(dog_id):
    """Soft-delete a dog."""
    current_user = get_current_user()
    return dog_service.delete_dog(dog_id, actor=current_user)


@dogs_bp.get("/<int:dog_id>/qr.png")
@dogs_bp.doc(
    summary="Download dog QR code PNG",
    description="Generate a QR code PNG encoding the public dog verification URL.",
    security="BearerAuth",
    responses={
        200: {
            "description": "QR Code PNG image",
            "content": {"image/png": {}},
        }
    },
)
@login_required
def get_dog_qr_png(dog_id):
    """Return a PNG QR code for the dog's public info URL."""
    png_bytes, dog_code = public_service.generate_dog_qr_png(dog_id)
    return Response(
        png_bytes,
        status=200,
        mimetype="image/png",
        headers={"Content-Disposition": f'inline; filename="{dog_code}.png"'},
    )

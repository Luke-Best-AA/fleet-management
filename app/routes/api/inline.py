from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.location import LocationCreateSchema
from app.schemas.user import UserCreateSchema
from app.security.csrf import validate_csrf_token
from app.services import location as location_service
from app.services import user as user_service

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/drivers")
async def create_driver(request: Request, db: Session = Depends(get_db)):
    """Create a new driver (standard user) via AJAX and return JSON."""
    user = request.state.user
    if not user or user["role"] != "admin":
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    data = await request.json()

    if not validate_csrf_token(data.get("csrf_token", "")):
        return JSONResponse({"error": "Invalid request."}, status_code=400)

    try:
        schema = UserCreateSchema(**data)
    except PydanticValidationError as e:
        errors = {}
        for err in e.errors():
            field = err["loc"][-1] if err["loc"] else "_general"
            errors[field] = err["msg"]
        return JSONResponse({"errors": errors}, status_code=422)

    try:
        new_user = user_service.create_user(
            db,
            username=schema.username,
            email=schema.email,
            password=schema.password,
            first_name=schema.first_name,
            last_name=schema.last_name,
            role="standard",
            employee_number=schema.employee_number,
            location_id=schema.location_id,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=422)

    return JSONResponse(
        {
            "id": new_user.id,
            "label": f"{new_user.first_name} {new_user.last_name} ({new_user.username})",
        }
    )


@router.post("/locations")
async def create_location(request: Request, db: Session = Depends(get_db)):
    """Create a new location via AJAX and return JSON."""
    user = request.state.user
    if not user or user["role"] != "admin":
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    data = await request.json()

    if not validate_csrf_token(data.get("csrf_token", "")):
        return JSONResponse({"error": "Invalid request."}, status_code=400)

    try:
        schema = LocationCreateSchema(**data)
    except PydanticValidationError as e:
        errors = {}
        for err in e.errors():
            field = err["loc"][-1] if err["loc"] else "_general"
            errors[field] = err["msg"]
        return JSONResponse({"errors": errors}, status_code=422)

    try:
        new_loc = location_service.create_location(
            db,
            name=schema.name,
            code=schema.code,
            region=schema.region,
            address_line_1=schema.address_line_1,
            address_line_2=schema.address_line_2,
            city=schema.city,
            postcode=schema.postcode,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=422)

    return JSONResponse(
        {
            "id": new_loc.id,
            "label": f"{new_loc.name} ({new_loc.code})",
        }
    )

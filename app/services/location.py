from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models.location import Location


def get_location_by_id(db: Session, location_id: int) -> Location:
    loc = db.query(Location).filter(Location.id == location_id, Location.is_deleted == False).first()
    if not loc:
        raise NotFoundError("Location not found")
    return loc


def get_all_locations(db: Session, active_only: bool = False) -> list[Location]:
    q = db.query(Location).filter(Location.is_deleted == False)
    if active_only:
        q = q.filter(Location.is_active == True)
    return q.order_by(Location.name).all()


def create_location(
    db: Session,
    name: str,
    code: str,
    region: str = "",
    address_line_1: str = "",
    address_line_2: str = "",
    city: str = "",
    postcode: str = "",
) -> Location:
    if db.query(Location).filter(Location.name == name, Location.is_deleted == False).first():
        raise ConflictError("Location name already in use")
    if db.query(Location).filter(Location.code == code, Location.is_deleted == False).first():
        raise ConflictError("Location code already in use")

    loc = Location(
        name=name,
        code=code,
        region=region or None,
        address_line_1=address_line_1 or None,
        address_line_2=address_line_2 or None,
        city=city or None,
        postcode=postcode or None,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def update_location(
    db: Session,
    location_id: int,
    name: str,
    code: str,
    region: str = "",
    address_line_1: str = "",
    address_line_2: str = "",
    city: str = "",
    postcode: str = "",
    is_active: bool = True,
) -> Location:
    loc = get_location_by_id(db, location_id)

    existing = (
        db.query(Location)
        .filter(Location.name == name, Location.id != location_id, Location.is_deleted == False)
        .first()
    )
    if existing:
        raise ConflictError("Location name already in use")

    existing = (
        db.query(Location)
        .filter(Location.code == code, Location.id != location_id, Location.is_deleted == False)
        .first()
    )
    if existing:
        raise ConflictError("Location code already in use")

    loc.name = name
    loc.code = code
    loc.region = region or None
    loc.address_line_1 = address_line_1 or None
    loc.address_line_2 = address_line_2 or None
    loc.city = city or None
    loc.postcode = postcode or None
    loc.is_active = is_active
    db.commit()
    db.refresh(loc)
    return loc


def soft_delete_location(db: Session, location_id: int) -> None:
    loc = get_location_by_id(db, location_id)
    loc.is_deleted = True
    db.commit()

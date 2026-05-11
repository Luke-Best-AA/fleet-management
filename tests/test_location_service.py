"""Tests for location service layer."""

import pytest

from app.exceptions import ConflictError, NotFoundError
from app.services import location as location_service


class TestGetLocationById:
    def test_returns_location(self, db, location):
        result = location_service.get_location_by_id(db, location.id)
        assert result.id == location.id
        assert result.name == "Test Depot"

    def test_raises_not_found(self, db):
        with pytest.raises(NotFoundError, match="Location not found"):
            location_service.get_location_by_id(db, 9999)

    def test_raises_not_found_for_deleted(self, db, location):
        location.is_deleted = True
        db.commit()
        with pytest.raises(NotFoundError, match="Location not found"):
            location_service.get_location_by_id(db, location.id)


class TestGetAllLocations:
    def test_returns_all(self, db, location):
        location_service.create_location(db, "Depot B", "DPB", city="CityB")
        locations = location_service.get_all_locations(db)
        assert len(locations) == 2

    def test_excludes_deleted(self, db, location):
        location.is_deleted = True
        db.commit()
        locations = location_service.get_all_locations(db)
        assert len(locations) == 0

    def test_active_only_filter(self, db, location):
        loc2 = location_service.create_location(db, "Inactive Depot", "INA")
        loc2.is_active = False
        db.commit()
        active = location_service.get_all_locations(db, active_only=True)
        assert len(active) == 1
        assert active[0].id == location.id

    def test_ordered_by_name(self, db):
        location_service.create_location(db, "Zebra Depot", "ZEB")
        location_service.create_location(db, "Alpha Depot", "ALP")
        locations = location_service.get_all_locations(db)
        assert locations[0].name == "Alpha Depot"
        assert locations[1].name == "Zebra Depot"


class TestCreateLocation:
    def test_create_minimal(self, db):
        loc = location_service.create_location(db, "New Depot", "NEW")
        assert loc.id is not None
        assert loc.name == "New Depot"
        assert loc.code == "NEW"

    def test_create_full(self, db):
        loc = location_service.create_location(
            db,
            "Full Depot",
            "FUL",
            region="North",
            address_line_1="123 Street",
            address_line_2="Unit 4",
            city="London",
            postcode="SW1A 1AA",
        )
        assert loc.region == "North"
        assert loc.city == "London"
        assert loc.postcode == "SW1A 1AA"

    def test_duplicate_name_fails(self, db, location):
        with pytest.raises(ConflictError, match="name already in use"):
            location_service.create_location(db, "Test Depot", "NEW")

    def test_duplicate_code_fails(self, db, location):
        with pytest.raises(ConflictError, match="code already in use"):
            location_service.create_location(db, "Other Depot", "TST")

    def test_empty_optional_fields_stored_as_none(self, db):
        loc = location_service.create_location(db, "Bare Depot", "BAR", region="", city="")
        assert loc.region is None
        assert loc.city is None


class TestUpdateLocation:
    def test_update_name(self, db, location):
        updated = location_service.update_location(
            db,
            location.id,
            "Renamed Depot",
            "TST",
        )
        assert updated.name == "Renamed Depot"

    def test_update_duplicate_name_fails(self, db, location):
        location_service.create_location(db, "Other Depot", "OTH")
        with pytest.raises(ConflictError, match="name already in use"):
            location_service.update_location(db, location.id, "Other Depot", "TST")

    def test_update_duplicate_code_fails(self, db, location):
        location_service.create_location(db, "Other Depot", "OTH")
        with pytest.raises(ConflictError, match="code already in use"):
            location_service.update_location(db, location.id, "Test Depot", "OTH")

    def test_update_same_name_ok(self, db, location):
        updated = location_service.update_location(
            db,
            location.id,
            "Test Depot",
            "TST",
        )
        assert updated.name == "Test Depot"

    def test_update_is_active(self, db, location):
        updated = location_service.update_location(
            db,
            location.id,
            "Test Depot",
            "TST",
            is_active=False,
        )
        assert updated.is_active is False


class TestSoftDeleteLocation:
    def test_soft_delete(self, db, location):
        location_service.soft_delete_location(db, location.id)
        db.refresh(location)
        assert location.is_deleted is True

    def test_soft_delete_nonexistent_raises(self, db):
        with pytest.raises(NotFoundError):
            location_service.soft_delete_location(db, 9999)

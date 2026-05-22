"""Tests for app.utils.forms helper functions."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_validator
from pydantic import ValidationError as PydanticValidationError

from app.utils.forms import parse_errors, safe_date, safe_decimal, safe_int, safe_int_or_none


class _Dummy(BaseModel):
    name: str
    age: int

    @field_validator("name")
    @classmethod
    def name_required(cls, v):
        if not v.strip():
            raise ValueError("Name is required")
        return v


class TestParseErrors:
    def test_missing_field(self):
        try:
            _Dummy(age=10)  # name missing
        except PydanticValidationError as e:
            errors = parse_errors(e)
        assert "name" in errors

    def test_int_parsing_error(self):
        try:
            _Dummy(name="Alice", age="abc")
        except PydanticValidationError as e:
            errors = parse_errors(e)
        assert "age" in errors
        assert "whole number" in errors["age"]

    def test_value_error_message(self):
        try:
            _Dummy(name="   ", age=10)
        except PydanticValidationError as e:
            errors = parse_errors(e)
        assert errors["name"] == "Name is required"


class TestSafeInt:
    def test_valid_int(self):
        assert safe_int("42") == 42

    def test_none_returns_default(self):
        assert safe_int(None) == 0

    def test_empty_returns_default(self):
        assert safe_int("") == 0

    def test_custom_default(self):
        assert safe_int(None, 5) == 5

    def test_invalid_returns_string(self):
        assert safe_int("abc") == "abc"


class TestSafeIntOrNone:
    def test_valid_int(self):
        assert safe_int_or_none("42") == 42

    def test_none_returns_none(self):
        assert safe_int_or_none(None) is None

    def test_empty_returns_none(self):
        assert safe_int_or_none("") is None

    def test_invalid_returns_string(self):
        assert safe_int_or_none("abc") == "abc"


class TestSafeDecimal:
    def test_valid_decimal(self):
        assert safe_decimal("12.50") == Decimal("12.50")

    def test_none_returns_none(self):
        assert safe_decimal(None) is None

    def test_empty_returns_none(self):
        assert safe_decimal("") is None

    def test_invalid_returns_string(self):
        assert safe_decimal("abc") == "abc"


class TestSafeDate:
    def test_valid_date(self):
        assert safe_date("2025-06-15") == date(2025, 6, 15)

    def test_none_returns_none(self):
        assert safe_date(None) is None

    def test_empty_returns_none(self):
        assert safe_date("") is None

    def test_invalid_returns_string(self):
        assert safe_date("not-a-date") == "not-a-date"

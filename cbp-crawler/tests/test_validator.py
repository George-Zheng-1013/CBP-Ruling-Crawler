"""Tests for the validator module."""

import pytest
from validator import RulingValidator, ValidationError, validate_ruling_batch


class TestValidationError:
    """Tests for ValidationError class."""

    def test_init(self):
        err = ValidationError("ruling_no", "Must be non-empty", "")
        assert err.field == "ruling_no"
        assert err.message == "Must be non-empty"
        assert err.value == ""

    def test_repr(self):
        err = ValidationError("year", "Invalid", 1999)
        r = repr(err)
        assert "year" in r
        assert "Invalid" in r

    def test_to_dict(self):
        err = ValidationError("hs_code", "Bad format", "12345")
        d = err.to_dict()
        assert d["field"] == "hs_code"
        assert d["message"] == "Bad format"
        assert d["value"] == "12345"


class TestRulingValidator:
    """Tests for RulingValidator class."""

    def make_valid_ruling(self, **overrides):
        ruling = {
            "ruling_no": "HQ12345",
            "subject": "Classification of widgets",
            "description": "This ruling classifies widgets under heading 8471. " * 5,
            "hs_code": "8471.30.0100",
            "hs_codes": ["8471.30.0100"],
            "year": 2023,
        }
        ruling.update(overrides)
        return ruling

    # ── Ruling No validation ──────────────────────────────────────────

    def test_valid_ruling_no(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling())
        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_ruling_no_empty(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(ruling_no=""))
        assert is_valid is False
        assert any(e.field == "ruling_no" for e in errors)

    def test_invalid_ruling_no_format(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(ruling_no="INVALID_FORMAT"))
        assert is_valid is False
        ruling_no_errors = [e for e in errors if e.field == "ruling_no"]
        assert len(ruling_no_errors) >= 1

    def test_duplicate_ruling_no(self):
        validator = RulingValidator()
        validator.validate(self.make_valid_ruling(ruling_no="HQ12345"))
        is_valid, errors = validator.validate(self.make_valid_ruling(ruling_no="HQ12345"))
        assert is_valid is False
        assert any("Duplicate" in e.message for e in errors)

    def test_duplicate_check_disabled(self):
        validator = RulingValidator()
        validator.validate(self.make_valid_ruling(ruling_no="HQ12345"))
        is_valid, errors = validator.validate(
            self.make_valid_ruling(ruling_no="HQ12345"),
            check_uniqueness=False,
        )
        # If check_uniqueness is False, duplicate should not trigger error
        duplicate_errors = [e for e in errors if "Duplicate" in e.message]
        assert len(duplicate_errors) == 0

    def test_valid_prefixes(self):
        for prefix in ("HQ", "NY", "N", "OT", "RR", "RUL", "W"):
            validator = RulingValidator()
            is_valid, errors = validator.validate(
                self.make_valid_ruling(ruling_no=f"{prefix}12345")
            )
            prefix_errors = [e for e in errors if e.field == "ruling_no" and "prefix" in e.message.lower()]
            assert len(prefix_errors) == 0, f"Prefix {prefix} should be valid"

    # ── Year validation ───────────────────────────────────────────────

    def test_valid_year(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(year=2023))
        assert is_valid is True

    def test_year_none(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(year=None))
        assert is_valid is False
        assert any(e.field == "year" for e in errors)

    def test_year_below_range(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(year=1999))
        assert is_valid is False
        assert any("outside valid range" in e.message for e in errors)

    def test_year_above_range(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(year=2027))
        assert is_valid is False
        assert any("outside valid range" in e.message for e in errors)

    def test_year_boundary_values(self):
        validator = RulingValidator()
        # 2000 should be valid
        is_valid, errors = validator.validate(
            self.make_valid_ruling(ruling_no="HQ10", year=2000)
        )
        assert is_valid is True, f"year=2000 errors: {errors}"
        # 2026 should be valid (use a fresh validator to avoid duplicate ruling_no)
        validator2 = RulingValidator()
        is_valid, errors = validator2.validate(
            self.make_valid_ruling(ruling_no="HQ20", year=2026)
        )
        assert is_valid is True, f"year=2026 errors: {errors}"

    def test_year_invalid_string(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(year="not_a_year"))
        assert is_valid is False
        assert any("not a valid integer" in e.message for e in errors)

    # ── HSCODE validation ─────────────────────────────────────────────

    def test_valid_hs_code(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(hs_code="8471.30.0100"))
        assert is_valid is True

    def test_hs_code_empty_allowed(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(hs_code=""))
        assert is_valid is True

    def test_invalid_hs_code_format(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(hs_code="8471300100"))
        assert is_valid is False
        assert any(e.field == "hs_code" for e in errors)

    def test_hs_code_wrong_length(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(hs_code="123.45.678"))
        assert is_valid is False

    def test_hs_codes_list_valid(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(
            self.make_valid_ruling(hs_codes=["8471.30.0100", "8473.30.5100"])
        )
        assert is_valid is True

    def test_hs_codes_list_invalid(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(
            self.make_valid_ruling(hs_codes=["not_a_code"])
        )
        assert is_valid is False
        assert any(e.field == "hs_codes" for e in errors)

    def test_hs_codes_not_a_list(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(
            self.make_valid_ruling(hs_codes="8471.30.0100")  # string, not list
        )
        assert is_valid is False
        assert any("must be a list" in e.message for e in errors)

    # ── Description validation ────────────────────────────────────────

    def test_description_empty(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(description=""))
        assert is_valid is False
        assert any(e.field == "description" for e in errors)

    def test_description_too_short(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(
            self.make_valid_ruling(description="Short")
        )
        assert is_valid is False
        assert any("too short" in e.message for e in errors)

    # ── Subject validation ────────────────────────────────────────────

    def test_subject_empty(self):
        validator = RulingValidator()
        is_valid, errors = validator.validate(self.make_valid_ruling(subject=""))
        assert is_valid is False
        assert any(e.field == "subject" for e in errors)


class TestValidatorReset:
    """Tests for the reset method."""

    def test_reset_clears_state(self):
        validator = RulingValidator()
        ruling = {
            "ruling_no": "HQ12345",
            "subject": "Test",
            "description": "A" * 100,
            "hs_code": "8471.30.0100",
            "hs_codes": ["8471.30.0100"],
            "year": 2023,
        }
        validator.validate(ruling)
        validator.reset()
        # After reset, same ruling should validate fine
        is_valid, errors = validator.validate(ruling)
        assert is_valid is True


class TestValidateRulingBatch:
    """Tests for validate_ruling_batch function."""

    def test_batch_all_valid(self):
        rulings = [
            {"ruling_no": f"HQ{100+i}", "subject": "Test", "description": "A" * 100,
             "hs_code": "8471.30.0100", "hs_codes": ["8471.30.0100"], "year": 2023}
            for i in range(3)
        ]
        result = validate_ruling_batch(rulings)
        assert result["total"] == 3
        assert result["valid"] == 3
        assert result["invalid"] == 0

    def test_batch_some_invalid(self):
        rulings = [
            {"ruling_no": "HQ100", "subject": "Test", "description": "A" * 100,
             "hs_code": "8471.30.0100", "hs_codes": ["8471.30.0100"], "year": 2023},
            {"ruling_no": "", "subject": "", "description": "",
             "hs_code": "", "hs_codes": [], "year": None},  # Invalid
        ]
        result = validate_ruling_batch(rulings)
        assert result["total"] == 2
        assert result["valid"] == 1
        assert result["invalid"] == 1

    def test_batch_empty(self):
        result = validate_ruling_batch([])
        assert result["total"] == 0
        assert result["valid"] == 0
        assert result["invalid"] == 0


class TestValidatorErrorsProperty:
    """Tests for the errors property."""

    def test_errors_property_returns_copy(self):
        validator = RulingValidator()
        # No validation yet
        assert validator.errors == []
        # Ensure it's a copy
        assert validator.errors is not validator._errors

    def test_errors_after_validation(self):
        validator = RulingValidator()
        ruling = {
            "ruling_no": "",
            "subject": "",
            "description": "",
            "hs_code": "",
            "hs_codes": [],
            "year": None,
        }
        validator.validate(ruling)
        assert len(validator.errors) >= 1

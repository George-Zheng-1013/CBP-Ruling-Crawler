"""Validation module for CBP Advance Ruling data.

Ensures data quality by validating ruling numbers, years, HSCODE formats,
and content completeness according to defined rules.
"""

import re
from typing import Dict, Any, List, Tuple, Optional

from utils import setup_logger

logger = setup_logger("validator")


class ValidationError:
    """Represents a single validation error.

    Attributes:
        field: The field that failed validation (e.g., 'ruling_no').
        message: Human-readable error description.
        value: The invalid value that was found.
    """

    def __init__(self, field: str, message: str, value: Any = None) -> None:
        """Initialize a ValidationError.

        Args:
            field: Field name.
            message: Error description.
            value: The problematic value.
        """
        self.field = field
        self.message = message
        self.value = value

    def __repr__(self) -> str:
        return (f"ValidationError(field={self.field}, "
                f"message={self.message}, value={self.value!r})")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dict with field, message, value keys.
        """
        return {
            "field": self.field,
            "message": self.message,
            "value": self.value,
        }


class RulingValidator:
    """Validates parsed ruling data against quality rules.

    Rules:
    1. Ruling No must be non-empty and follow the expected pattern
    2. Ruling No must be unique (no duplicates in the provided set)
    3. Year must be in range [2000, 2026]
    4. HSCODE must match the 10-digit format (XXXX.XX.XXXX)
    5. Description must be non-empty
    """

    # Valid prefix patterns for ruling numbers
    VALID_PREFIXES = ("HQ", "NY", "N", "OT", "RR", "RUL", "W")
    # HSCODE regex pattern (format: XXXX.XX.XXXX)
    HSCODE_REGEX = re.compile(r"^\d{4}\.\d{2}\.\d{4}$")
    # Ruling number regex pattern
    RULING_NO_REGEX = re.compile(r"^[A-Z]{1,3}\d{2,6}$")

    def __init__(self) -> None:
        """Initialize the validator."""
        self._errors: List[ValidationError] = []
        self._seen_ruling_nos: set = set()

    def validate(self, ruling: Dict[str, Any],
                 check_uniqueness: bool = True) -> Tuple[bool, List[ValidationError]]:
        """Validate a single parsed ruling record.

        Args:
            ruling: Dict with parsed ruling data (keys: ruling_no, subject,
                    description, hs_code, hs_codes, year, etc.).
            check_uniqueness: If True, check that ruling_no is unique
                              across this validator instance.

        Returns:
            Tuple of (is_valid: bool, errors: list of ValidationError).
        """
        self._errors = []

        self._validate_ruling_no(ruling.get("ruling_no", ""), check_uniqueness)
        self._validate_year(ruling.get("year"))
        self._validate_hs_code(ruling.get("hs_code", ""))
        self._validate_hs_codes(ruling.get("hs_codes", []))
        self._validate_description(ruling.get("description", ""))
        self._validate_subject(ruling.get("subject", ""))

        return len(self._errors) == 0, self._errors

    def _validate_ruling_no(self, ruling_no: str,
                            check_uniqueness: bool) -> None:
        """Validate ruling number format and uniqueness.

        Args:
            ruling_no: The ruling number string.
            check_uniqueness: Whether to check for duplicates.
        """
        if not ruling_no or not ruling_no.strip():
            self._errors.append(ValidationError(
                field="ruling_no",
                message="Ruling No must be non-empty",
                value=ruling_no,
            ))
            return

        ruling_no = ruling_no.strip().upper()

        # Check format: letter prefix + digits
        if not self.RULING_NO_REGEX.match(ruling_no):
            self._errors.append(ValidationError(
                field="ruling_no",
                message=(f"Ruling No '{ruling_no}' does not match expected "
                         f"pattern (letter prefix + digits)"),
                value=ruling_no,
            ))

        # Check for known valid prefix
        has_valid_prefix = any(
            ruling_no.startswith(p) for p in self.VALID_PREFIXES
        )
        if not has_valid_prefix:
            self._errors.append(ValidationError(
                field="ruling_no",
                message=(f"Ruling No '{ruling_no}' does not start with a "
                         f"known prefix: {self.VALID_PREFIXES}"),
                value=ruling_no,
            ))

        # Check uniqueness
        if check_uniqueness:
            if ruling_no in self._seen_ruling_nos:
                self._errors.append(ValidationError(
                    field="ruling_no",
                    message=f"Duplicate ruling number: {ruling_no}",
                    value=ruling_no,
                ))
            else:
                self._seen_ruling_nos.add(ruling_no)

    def _validate_year(self, year: Any) -> None:
        """Validate the year is in the expected range.

        Args:
            year: Year value (int, str, or None).
        """
        if year is None:
            self._errors.append(ValidationError(
                field="year",
                message="Year must not be None",
                value=year,
            ))
            return

        try:
            year_int = int(year)
        except (ValueError, TypeError):
            self._errors.append(ValidationError(
                field="year",
                message=f"Year '{year}' is not a valid integer",
                value=year,
            ))
            return

        if year_int < 2000 or year_int > 2026:
            self._errors.append(ValidationError(
                field="year",
                message=f"Year {year_int} is outside valid range (2000-2026)",
                value=year_int,
            ))

    def _validate_hs_code(self, hs_code: str) -> None:
        """Validate the primary HSCODE format.

        HSCODE must be a 10-digit code in format XXXX.XX.XXXX.
        Empty is allowed (not all rulings have HS codes).

        Args:
            hs_code: The primary HSCODE string.
        """
        if not hs_code or not hs_code.strip():
            return  # Empty is acceptable

        hs_code = hs_code.strip()
        if not self.HSCODE_REGEX.match(hs_code):
            self._errors.append(ValidationError(
                field="hs_code",
                message=(f"HSCODE '{hs_code}' does not match expected "
                         f"format (XXXX.XX.XXXX)"),
                value=hs_code,
            ))

    def _validate_hs_codes(self, hs_codes: Any) -> None:
        """Validate the list of HSCODEs.

        Args:
            hs_codes: List of HSCODE strings.
        """
        if not hs_codes:
            return

        if not isinstance(hs_codes, list):
            self._errors.append(ValidationError(
                field="hs_codes",
                message=f"hs_codes must be a list, got {type(hs_codes).__name__}",
                value=hs_codes,
            ))
            return

        for i, code in enumerate(hs_codes):
            if not isinstance(code, str) or not self.HSCODE_REGEX.match(code):
                self._errors.append(ValidationError(
                    field="hs_codes",
                    message=(f"HSCODE at index {i} '{code}' does not match "
                             f"expected format (XXXX.XX.XXXX)"),
                    value=code,
                ))

    def _validate_description(self, description: str) -> None:
        """Validate that the description/body text is non-empty.

        Args:
            description: The ruling body text.
        """
        if not description or not description.strip():
            self._errors.append(ValidationError(
                field="description",
                message="Description must be non-empty",
                value=description,
            ))
        elif len(description.strip()) < 50:
            self._errors.append(ValidationError(
                field="description",
                message=(f"Description is too short "
                         f"({len(description.strip())} chars, minimum 50)"),
                value=description[:100],
            ))

    def _validate_subject(self, subject: str) -> None:
        """Validate the subject line is non-empty.

        Args:
            subject: The ruling subject/title.
        """
        if not subject or not subject.strip():
            self._errors.append(ValidationError(
                field="subject",
                message="Subject must be non-empty",
                value=subject,
            ))

    @property
    def errors(self) -> List[ValidationError]:
        """Get the list of validation errors from the last validation.

        Returns:
            List of ValidationError objects.
        """
        return self._errors.copy()

    def reset(self) -> None:
        """Reset the validator state (clears seen ruling numbers and errors)."""
        self._errors = []
        self._seen_ruling_nos = set()


def validate_ruling_batch(rulings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate a batch of rulings and return summary statistics.

    Args:
        rulings: List of parsed ruling dicts.

    Returns:
        Dict with keys:
            - total: Total number of rulings checked
            - valid: Number of valid rulings
            - invalid: Number of invalid rulings
            - errors: Dict mapping ruling_no -> list of error dicts
    """
    validator = RulingValidator()
    results: Dict[str, Any] = {
        "total": len(rulings),
        "valid": 0,
        "invalid": 0,
        "errors": {},
    }

    for ruling in rulings:
        ruling_no = ruling.get("ruling_no", "UNKNOWN")
        is_valid, errors = validator.validate(ruling)

        if is_valid:
            results["valid"] += 1
        else:
            results["invalid"] += 1
            results["errors"][ruling_no] = [e.to_dict() for e in errors]

    return results

"""Tests for validation utilities per ADR-018.

Tests comprehensive error reporting and type coercion for improved LLM experience.
"""

import pytest
from pydantic import BaseModel, Field, ValidationError, field_validator

from hiro.core.mcp.validation import (
    coerce_bool,
    coerce_float,
    coerce_int,
    format_validation_errors,
)


# Test model for validation
class SampleParams(BaseModel):
    """Test model with various field types."""

    name: str = Field(description="Name field")
    age: int = Field(description="Age field", ge=0, le=150)
    active: bool = Field(description="Active status")
    score: float | None = Field(None, description="Optional score")

    @field_validator("active", mode="before")
    @classmethod
    def coerce_active(cls, v):
        return coerce_bool(v)

    @field_validator("age", mode="before")
    @classmethod
    def coerce_age(cls, v):
        return coerce_int(v)

    @field_validator("score", mode="before")
    @classmethod
    def coerce_score(cls, v):
        if v is None:
            return None
        return coerce_float(v)


class TestFormatValidationErrors:
    """Test comprehensive error formatting."""

    @pytest.mark.unit
    def test_single_error_formatting(self):
        """Test formatting when there's only one validation error."""
        # Arrange
        try:
            SampleParams(name=123, age=25, active=True)  # name should be string
        except ValidationError as e:
            # Act
            result = format_validation_errors(e, "test parameters")

            # Assert
            assert "Invalid test parameters:" in result
            assert "name" in result
            assert "received: 123" in result
            assert "string" in result.lower()

    @pytest.mark.unit
    def test_multiple_errors_formatting(self):
        """Test formatting with multiple validation errors."""
        # Arrange
        try:
            # Multiple errors: name wrong type, age out of range, active wrong type
            SampleParams(name=123, age=200, active="invalid")
        except ValidationError as e:
            # Act
            result = format_validation_errors(e, "test parameters")

            # Assert
            assert "Invalid test parameters - 3 errors:" in result
            assert "• name:" in result
            assert "• age:" in result
            assert "• active:" in result
            assert "Please fix all errors and retry" in result

    @pytest.mark.unit
    def test_nested_field_path(self):
        """Test formatting with nested field paths."""

        # Arrange
        class NestedModel(BaseModel):
            inner: SampleParams

        try:
            NestedModel(inner={"name": 123, "age": 25, "active": True})
        except ValidationError as e:
            # Act
            result = format_validation_errors(e, "nested model")

            # Assert
            assert "inner.name" in result

    @pytest.mark.unit
    def test_missing_required_fields(self):
        """Test formatting when required fields are missing."""
        # Arrange
        try:
            SampleParams()  # Missing all required fields
        except ValidationError as e:
            # Act
            result = format_validation_errors(e, "test parameters")

            # Assert
            assert "3 errors" in result
            assert "name" in result
            assert "age" in result
            assert "active" in result


class TestTypeCoercion:
    """Test type coercion functions for common LLM mistakes."""

    @pytest.mark.unit
    def test_coerce_bool_true_values(self):
        """Test coercing various true representations."""
        # Arrange & Act & Assert
        assert coerce_bool("true") is True
        assert coerce_bool("True") is True
        assert coerce_bool("TRUE") is True
        assert coerce_bool("1") is True
        assert coerce_bool("yes") is True
        assert coerce_bool("on") is True

    @pytest.mark.unit
    def test_coerce_bool_false_values(self):
        """Test coercing various false representations."""
        # Arrange & Act & Assert
        assert coerce_bool("false") is False
        assert coerce_bool("False") is False
        assert coerce_bool("FALSE") is False
        assert coerce_bool("0") is False
        assert coerce_bool("no") is False
        assert coerce_bool("off") is False
        assert coerce_bool("") is False

    @pytest.mark.unit
    def test_coerce_bool_passthrough(self):
        """Test that non-string values pass through unchanged."""
        # Arrange & Act & Assert
        assert coerce_bool(True) is True
        assert coerce_bool(False) is False
        assert coerce_bool(None) is None
        assert coerce_bool("invalid") == "invalid"  # Unknown string passes through
        assert coerce_bool(123) == 123

    @pytest.mark.unit
    def test_coerce_int_valid_strings(self):
        """Test coercing valid integer strings."""
        # Arrange & Act & Assert
        assert coerce_int("123") == 123
        assert coerce_int("0") == 0
        assert coerce_int("-456") == -456
        assert coerce_int("  789  ") == 789  # With whitespace

    @pytest.mark.unit
    def test_coerce_int_passthrough(self):
        """Test that non-string or invalid values pass through."""
        # Arrange & Act & Assert
        assert coerce_int(123) == 123
        assert coerce_int(None) is None
        assert coerce_int("not a number") == "not a number"
        assert coerce_int("12.34") == "12.34"  # Float string doesn't coerce to int
        assert coerce_int([1, 2, 3]) == [1, 2, 3]

    @pytest.mark.unit
    def test_coerce_float_valid_strings(self):
        """Test coercing valid float strings."""
        # Arrange & Act & Assert
        assert coerce_float("123.45") == 123.45
        assert coerce_float("0.0") == 0.0
        assert coerce_float("-78.9") == -78.9
        assert coerce_float("123") == 123.0  # Integer strings work too
        assert coerce_float("  45.67  ") == 45.67  # With whitespace

    @pytest.mark.unit
    def test_coerce_float_passthrough(self):
        """Test that non-string or invalid values pass through."""
        # Arrange & Act & Assert
        assert coerce_float(123.45) == 123.45
        assert coerce_float(None) is None
        assert coerce_float("not a number") == "not a number"
        assert coerce_float([1.0, 2.0]) == [1.0, 2.0]


class TestIntegrationWithPydantic:
    """Test integration of coercion with Pydantic models."""

    @pytest.mark.unit
    def test_model_with_coercion_accepts_string_bools(self):
        """Test that model with coercion accepts string booleans."""
        # Arrange
        data = {"name": "Alice", "age": "30", "active": "true"}

        # Act
        result = SampleParams(**data)

        # Assert
        assert result.name == "Alice"
        assert result.age == 30  # Coerced from string
        assert result.active is True  # Coerced from string

    @pytest.mark.unit
    def test_model_with_coercion_accepts_string_numbers(self):
        """Test that model with coercion accepts string numbers."""
        # Arrange
        data = {"name": "Bob", "age": "25", "active": "false", "score": "98.5"}

        # Act
        result = SampleParams(**data)

        # Assert
        assert result.age == 25  # Coerced from string
        assert result.score == 98.5  # Coerced from string

    @pytest.mark.unit
    def test_model_rejects_invalid_even_with_coercion(self):
        """Test that invalid values still fail validation."""
        # Arrange
        data = {"name": "Charlie", "age": "not_a_number", "active": "yes"}

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            SampleParams(**data)

        # Verify the error message contains the field
        errors = exc_info.value.errors()
        assert any(err["loc"] == ("age",) for err in errors)

    @pytest.mark.unit
    def test_comprehensive_error_with_coercion(self):
        """Test comprehensive errors when multiple fields fail even with coercion."""
        # Arrange
        try:
            SampleParams(
                name="",  # Empty string might be invalid
                age="999",  # Out of range even after coercion
                active="maybe",  # Can't coerce to bool
            )
        except ValidationError as e:
            # Act
            result = format_validation_errors(e, "test parameters")

            # Assert
            assert "999" in result  # Shows the coerced value that still failed
            assert "maybe" in result  # Shows the value that couldn't be coerced
            assert "errors" in result

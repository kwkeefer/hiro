"""Test boolean coercion in AI logging tools."""

import pytest

from hiro.servers.ai_logging.tools import UpdateTargetContextParams


class TestUpdateTargetContextParamsBooleanCoercion:
    """Test boolean parameter coercion in UpdateTargetContextParams."""

    @pytest.mark.unit
    def test_string_true_false_coercion(self):
        """Test that string 'true'/'false' values are coerced to booleans."""
        # Arrange
        target_id = "617c4586-82a6-43e4-951f-0b6bcc5951c3"

        # Act
        params = UpdateTargetContextParams(
            target_id=target_id, is_major_version="true", append_mode="false"
        )

        # Assert
        assert params.is_major_version is True
        assert params.append_mode is False
        assert isinstance(params.is_major_version, bool)
        assert isinstance(params.append_mode, bool)

    @pytest.mark.unit
    def test_actual_boolean_values(self):
        """Test that actual boolean values work correctly."""
        # Arrange
        target_id = "617c4586-82a6-43e4-951f-0b6bcc5951c3"

        # Act
        params = UpdateTargetContextParams(
            target_id=target_id, is_major_version=True, append_mode=False
        )

        # Assert
        assert params.is_major_version is True
        assert params.append_mode is False
        assert isinstance(params.is_major_version, bool)
        assert isinstance(params.append_mode, bool)

    @pytest.mark.unit
    def test_various_truthy_string_representations(self):
        """Test various string representations that should coerce to True."""
        # Arrange
        target_id = "617c4586-82a6-43e4-951f-0b6bcc5951c3"
        truthy_values = ["True", "1", "yes", "on"]

        for value in truthy_values:
            # Act
            params = UpdateTargetContextParams(
                target_id=target_id, is_major_version=value
            )

            # Assert
            assert (
                params.is_major_version is True
            ), f"Value '{value}' should coerce to True"

    @pytest.mark.unit
    def test_various_falsy_string_representations(self):
        """Test various string representations that should coerce to False."""
        # Arrange
        target_id = "617c4586-82a6-43e4-951f-0b6bcc5951c3"
        falsy_values = ["False", "0", "no", "off"]

        for value in falsy_values:
            # Act
            params = UpdateTargetContextParams(
                target_id=target_id, is_major_version=value
            )

            # Assert
            assert (
                params.is_major_version is False
            ), f"Value '{value}' should coerce to False"

    @pytest.mark.unit
    def test_default_boolean_values(self):
        """Test that default boolean values are set correctly."""
        # Arrange
        target_id = "617c4586-82a6-43e4-951f-0b6bcc5951c3"

        # Act
        params = UpdateTargetContextParams(target_id=target_id)

        # Assert
        assert params.is_major_version is False
        assert params.append_mode is False

    @pytest.mark.unit
    def test_mixed_boolean_parameter_types(self):
        """Test mixing string and boolean parameter types."""
        # Arrange
        target_id = "617c4586-82a6-43e4-951f-0b6bcc5951c3"

        # Act
        params = UpdateTargetContextParams(
            target_id=target_id,
            is_major_version="true",  # String
            append_mode=True,  # Boolean
        )

        # Assert
        assert params.is_major_version is True
        assert params.append_mode is True
        assert isinstance(params.is_major_version, bool)
        assert isinstance(params.append_mode, bool)

    @pytest.mark.unit
    def test_function_signature_accepts_string_booleans(self):
        """Test that the actual function signature accepts string boolean values."""
        import inspect

        from hiro.servers.ai_logging.tools import UpdateTargetContextTool

        # Arrange
        tool = UpdateTargetContextTool()
        sig = inspect.signature(tool.execute)

        # Act & Assert - Check that boolean parameters accept str | bool
        append_mode_param = sig.parameters["append_mode"]
        is_major_version_param = sig.parameters["is_major_version"]

        # The annotation should be Union[bool, str] or bool | str
        assert "str" in str(append_mode_param.annotation)
        assert "bool" in str(append_mode_param.annotation)
        assert "str" in str(is_major_version_param.annotation)
        assert "bool" in str(is_major_version_param.annotation)

# Testing Standards

## Test Organization
Tests mirror source structure:
- `src/code_mcp/core/feature.py`
- `tests/core/test_feature.py`

## Markers (Required)
```python
@pytest.mark.unit         # No external deps, <100ms
@pytest.mark.integration  # External deps (DB, API)
@pytest.mark.slow        # >1 second
```

## AAA Pattern (Always Use)
```python
def test_feature_behavior(self):
    # Arrange - Set up test data
    user = User(name="test")
    service = Service()
    
    # Act - Execute the behavior
    result = service.process(user)
    
    # Assert - Verify outcomes
    assert result.status == "success"
    assert user.processed is True
```

Keep each section distinct. Use blank lines to separate if needed.

## Patterns

### Basic Test Structure
```python
class TestFeatureName:
    """Group related tests."""
    
    @pytest.mark.unit
    def test_happy_path(self):
        # Arrange
        input_data = {"key": "value"}
        
        # Act
        result = feature(input_data)
        
        # Assert
        assert result == expected
    
    @pytest.mark.unit
    def test_edge_case(self):
        # Arrange
        invalid_input = ""
        
        # Act & Assert
        with pytest.raises(ValueError):
            feature(invalid_input)
```

### Fixtures
Define in `tests/conftest.py` for sharing.

### Coverage
Aim for >80%. Check with `make test-cov`.

## Commands
- `make test` - All tests
- `make test-unit` - Fast tests only
- `make test-integration` - Integration only
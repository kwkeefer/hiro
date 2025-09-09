# code-mcp

Getting started with MCP stuff

## Features

- Modern Python 3.12 project with src layout
- Dependency management with [uv](https://github.com/astral-sh/uv)
- Testing with pytest
- Code formatting with ruff
- Type checking with mypy
- CLI interface with click
- Docker support for containerization
- GitHub Actions for CI/CD
- Pre-commit hooks for code quality
- Claude Code agents for automated code review

## Installation

### For Development

```bash
# Clone the repository
git clone https://github.com/kwkeefer/code_mcp.git
cd code_mcp

# Set up development environment
make dev
```

### For Production

```bash
# Install with uv
uv pip install code_mcp

# Or install from source
make install
```

## Usage

### Command Line Interface

```bash
# Run the CLI
code_mcp --help

# Or using make
make run
```

### As a Library

```python
from code_mcp import __version__
```

## Development

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration
```

### Code Quality

```bash
# Run linting
make lint

# Format code
make format

# Type checking
make typecheck
```

### Building

```bash
# Build distribution packages
make build
```

### Docker

```bash
# Build Docker image
make docker-build

# Run Docker container
make docker-run

# Using docker-compose
make docker-compose-up
make docker-compose-down
```

## Project Structure

```
code_mcp/
├── src/
│   └── code_mcp/
│       ├── __init__.py
│       ├── core/           # Core business logic
│       ├── api/            # API interfaces
│       ├── db/             # Database models and queries
│       └── utils/          # Utility functions
├── tests/                  # Test suite (mirrors src structure)
│   ├── conftest.py
│   ├── core/
│   ├── api/
│   ├── db/
│   └── utils/
├── docs/                   # Documentation
├── config/                 # Configuration files
├── scripts/                # Utility scripts
├── pyproject.toml          # Project configuration
├── Makefile                # Development commands
└── README.md               # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Kyle Keefer - kwkeefer@gmail.com

## Acknowledgments

- Built with [cookiecutter-uv](https://github.com/kwkeefer/cookiecutter-uv)
- Package management by [uv](https://github.com/astral-sh/uv)

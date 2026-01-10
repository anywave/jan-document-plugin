# Contributing to Jan Document Plugin

Thank you for your interest in contributing to Jan Document Plugin! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. Be kind to others, welcome newcomers, and focus on constructive feedback.

## How to Contribute

### Reporting Bugs

Before submitting a bug report:

1. **Check existing issues** - Your bug may already be reported
2. **Use the latest version** - Ensure you're running the latest release
3. **Run diagnostics** - Execute `tutorial.bat` and select "Verify Installation"

When reporting bugs, include:

- Your Windows version (10/11)
- Python version (`python --version`)
- Jan AI version
- Steps to reproduce the issue
- Expected vs actual behavior
- Console output or error messages
- Relevant log files (`install_log.txt`, `server.log`)

### Suggesting Features

We welcome feature suggestions! Please:

1. Check if the feature has already been suggested
2. Clearly describe the use case
3. Explain how it benefits users
4. Consider implementation complexity

### Pull Requests

#### First-Time Setup

1. **Fork the repository**
   ```bash
   # Click "Fork" on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/jan-document-plugin.git
   cd jan-document-plugin
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

#### Development Workflow

1. **Make your changes**
   - Follow the code style guidelines below
   - Add tests if applicable
   - Update documentation as needed

2. **Test your changes**
   ```bash
   # Run the calibration verification
   python calibration/verify_extraction.py

   # Test the installer
   install_debug.bat --debug

   # Run the server with debug mode
   JanDocumentPlugin.bat --debug
   ```

3. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - New features
   - `fix:` - Bug fixes
   - `docs:` - Documentation changes
   - `refactor:` - Code refactoring
   - `test:` - Adding or updating tests
   - `chore:` - Maintenance tasks

4. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a Pull Request on GitHub.

## Code Style Guidelines

### Python

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and small
- Use type hints where practical

```python
def process_document(file_path: str, chunk_size: int = 1000) -> List[str]:
    """
    Process a document and return text chunks.

    Args:
        file_path: Path to the document file
        chunk_size: Maximum characters per chunk

    Returns:
        List of text chunks
    """
    # Implementation
```

### Batch Scripts

- Include header comments explaining purpose
- Use `setlocal EnableDelayedExpansion` for variable expansion
- Add `REM` comments for complex logic
- Handle errors gracefully with clear messages
- Support `--help` flag for documentation

### Documentation

- Use clear, concise language
- Include code examples where helpful
- Keep README.md up to date
- Add inline comments for complex code

## Project Structure

```
jan-document-plugin/
├── jan_proxy.py              # Main server (modify carefully)
├── document_processor.py     # Document extraction
├── requirements.txt          # Dependencies
├── config.env               # Configuration
│
├── JanDocumentPlugin.bat     # Main launcher
├── install.bat              # Standard installer
├── install_debug.bat        # Debug installer
├── tutorial.bat             # Setup wizard
│
├── calibration/             # Verification tools
│   ├── create_calibration_pdf.py
│   ├── verify_extraction.py
│   └── JanDocPlugin_Calibration.pdf
│
├── docs/                    # Additional documentation
└── .github/                 # GitHub templates
```

## Areas for Contribution

### High Priority

- **Additional file format support** - Add extractors for new document types
- **Performance optimization** - Improve chunking and embedding speed
- **Cross-platform support** - Add macOS/Linux support
- **Error handling** - Improve error messages and recovery

### Medium Priority

- **UI improvements** - Enhance the web interface
- **Configuration options** - Add more customization
- **Caching** - Implement document caching
- **Batch processing** - Support bulk document uploads

### Documentation

- **Tutorials** - Step-by-step guides for specific use cases
- **Troubleshooting** - Document common issues and solutions
- **API examples** - More code examples for API usage

## Testing

### Manual Testing

1. Run the installation with debug mode:
   ```bash
   install_debug.bat --debug
   ```

2. Verify with calibration PDF:
   ```bash
   python calibration/verify_extraction.py
   ```

3. Test document upload and retrieval manually

### Adding Tests

If adding automated tests:

- Place test files in `tests/` directory
- Use `pytest` for Python tests
- Name test files `test_*.py`
- Test both success and failure cases

## Getting Help

- **Questions**: Open a [GitHub Discussion](https://github.com/AnyWaveCreations/jan-document-plugin/discussions)
- **Bugs**: Open a [GitHub Issue](https://github.com/AnyWaveCreations/jan-document-plugin/issues)
- **Security**: Email security concerns privately (do not open public issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping improve Jan Document Plugin!

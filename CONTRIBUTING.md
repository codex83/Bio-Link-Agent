# Contributing to Bio-Link Agent

Thank you for your interest in contributing to Bio-Link Agent! This document provides guidelines and instructions for contributing.

## Getting Started

1. **Fork the repository**
2. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/bio-link-agent.git
   cd bio-link-agent
   ```

3. **Set up development environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Create `.env` file**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

## Development Workflow

1. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**

3. **Test your changes**:
   ```bash
   python test_setup.py
   streamlit run app.py  # Test the app
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

5. **Push and create a Pull Request**

## Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and modular

## Testing

- Run `python test_setup.py` to verify setup
- Test the Streamlit app manually
- Ensure no hardcoded credentials

## Pull Request Guidelines

- Provide a clear description of changes
- Reference any related issues
- Ensure all tests pass
- Update documentation if needed

## Questions?

Open an issue for questions or discussions about contributions.


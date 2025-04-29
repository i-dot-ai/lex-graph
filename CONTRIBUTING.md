# Lex Graph Build - Contribution Guide 📝

## Setup 🛠️

1. Clone the repo
```bash
git clone https://github.com/i-dot-ai/lex-graph-build.git
```


2. Install poetry if you don't have it
```bash
pip install poetry
```

3. Install the dependencies and create a virtual environment
```bash
poetry install
```

4. Install pre-commits
```bash
pre-commit install
```

## Testing 🧪

Run the test suite:
```bash
poetry run pytest
```

Run a specific file:
```bash
poetry run pytest <file_name>
```

Run a specific test:
```bash
poetry run pytest -k <test_name>
```

Run with coverage:
```bash
poetry run pytest --cov=src
```

## Linting 🧹

Linting should get done automatically before each commit via pre-commit hooks.

To manually lint the code you can run the pre-commit hooks:
```bash
pre-commit run --all-files
```


## Dependencies 📦

Add a new dependency:
```bash
poetry add <package_name>
```

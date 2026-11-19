# Contributing

## Development

To get started:

```sh
uv venv --python 3.11
uv pip install -e ".[dev]"
uv run pre-commit install
```

Run the checks:

```sh
uv run ruff format node
uv run ruff check --select I --fix node
uv run ruff check node
uv run ty check
```

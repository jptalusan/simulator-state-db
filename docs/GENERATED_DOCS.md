# To generate HTML docs:

1. **Install dev dependencies** (if not already):
```bash
uv sync --extra dev
```

2. **Generate the docs**:
```bash
uv run sphinx-build -b html docs docs/_build/html
```

3. **Open the docs**:
```bash
open docs/_build/html/index.html
```

Or use the sphinx-autobuild for live reload during development:
```bash
uv pip install sphinx-autobuild
uv run sphinx-autobuild docs docs/_build/html
```

The `conf.py` is already in your docs folder, so Sphinx should be ready to go.

# FastApi docs

1. **Run the fast api via uvicorn**
```bash
uvicorn simulation_db.api.app:app --reload --host 0.0.0.0 --port 8000
```

2. **Access docs**
[redoc](http://127.0.0.1:8000/redoc)
[docs](http://127.0.0.1:8000/docs)
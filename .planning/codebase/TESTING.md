# Testing Patterns

**Analysis Date:** 2026-03-11

## Test Framework

**Runner:**
- Not configured. No test framework is installed or set up.

**No test dependencies in `requirements.txt`:**
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
httpx==0.28.1
pydantic==2.10.4
python-dotenv==1.0.1
```

No pytest, unittest, or any test runner is present. No `pyproject.toml`, `setup.py`, `setup.cfg`, `tox.ini`, or `pytest.ini` configuration files exist.

## Test File Organization

**Location:**
- No test files exist anywhere in the project.
- No `tests/` directory.
- No `test_*.py` or `*_test.py` files.
- No `conftest.py` files.

## Test Coverage

**Requirements:** None enforced. No coverage tooling installed.

**Current coverage:** 0% -- no tests exist.

## What Needs Testing

The following areas have zero test coverage and represent the recommended testing priorities:

### Priority 1: Core Business Logic (`agent.py`)

**`_decide_distribution()` (line 21-51):**
- Pure function, easily testable
- Takes `batch_type`, `quantity`, and `magnets` list
- Returns a distribution dict mapping awareness stages to counts
- Has three branches (exposure, sales, mixed) with sub-logic
- Example test:
```python
def test_decide_distribution_exposure():
    result = _decide_distribution("חשיפה", 10, [])
    assert result == {"Unaware": 6, "Problem-Aware": 4}

def test_decide_distribution_sales_no_magnets():
    result = _decide_distribution("מכירה", 10, [])
    assert result == {"Problem-Aware": 6, "Solution-Aware": 4}

def test_decide_distribution_sales_with_magnets():
    result = _decide_distribution("מכירה", 10, [{"id": "rec1"}])
    assert result == {"Problem-Aware": 4, "Solution-Aware": 6}
```

**`_build_queue_record()` (line 83-102):**
- Pure function, easily testable
- Converts a reel dict into Airtable-shaped record
- Handles optional `magnet_id` field

**`generate_reels()` validation (line 105-119):**
- Input validation (`batch_type` membership, `quantity` range)
- Requires mocking of `airtable_client` and `ollama_client`

### Priority 2: Prompt Formatting (`prompts.py`)

All `format_*` functions are pure and easily testable:

- **`format_magnets()` (line 104):** handles empty list, formats with field extraction
- **`format_style_examples()` (line 123):** handles empty list, truncates long strings at 200 chars
- **`format_hooks()` (line 143):** handles empty list, respects `limit` parameter
- **`format_viral_content()` (line 157):** handles empty list, respects `limit` parameter
- **`format_rtm_events()` (line 174):** handles empty list
- **`format_insights()` (line 189):** handles `None` input
- **`format_distribution()` (line 204):** maps stage names to descriptions
- **`build_generation_prompt()` (line 217):** assembles all parts into final prompt

### Priority 3: JSON Parsing (`ollama_client.py`)

**`generate_json()` (line 53-85):**
- Contains non-trivial JSON extraction logic
- Strips markdown code fences
- Attempts to find JSON within raw text
- Edge cases: malformed JSON, nested fences, missing delimiters
- Example test:
```python
async def test_generate_json_strips_code_fences(monkeypatch):
    async def mock_generate(prompt, system=None):
        return '```json\n{"reels": []}\n```'
    monkeypatch.setattr("ollama_client.generate", mock_generate)
    result = await generate_json("test prompt")
    assert result == {"reels": []}
```

### Priority 4: Airtable Client (`airtable_client.py`)

**`_fetch_all()` (line 17-56):**
- Pagination logic (offset handling)
- Parameter construction for filters, fields, sort
- Requires httpx mocking or `respx` library

**`_create_records_batch()` (line 71-89):**
- Batching logic (groups of 10)
- Requires httpx mocking

### Priority 5: API Routes (`main.py`)

**FastAPI route tests using `httpx.AsyncClient` with `app`:**
- `GET /health` -- verifies health check response structure
- `POST /generate` -- verifies request validation, error handling
- `POST /generate-async` -- verifies 202 response, batch_type validation
- `GET /models` -- verifies model listing

FastAPI provides `TestClient` or async testing via `httpx.AsyncClient`:
```python
from httpx import ASGITransport, AsyncClient
from main import app

async def test_health_check():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "ollama" in data
```

### Priority 6: Background Task (`main.py`)

**`_run_generation_and_callback()` (line 110-226):**
- Retry logic with exponential backoff
- Error callback on failure
- Magnet name resolution via `_resolve_magnet_name()`
- Complex to test, requires mocking multiple services

## Recommended Test Setup

**Install test dependencies:**
```bash
pip install pytest pytest-asyncio httpx respx
```

**Add to `requirements.txt` (or create `requirements-dev.txt`):**
```
pytest>=8.0
pytest-asyncio>=0.24
respx>=0.22       # httpx mocking
coverage>=7.0
```

**Create `pytest.ini` or add to `pyproject.toml`:**
```ini
[tool:pytest]
asyncio_mode = auto
testpaths = tests
```

**Recommended file structure:**
```
tests/
├── conftest.py              # Shared fixtures (mock Airtable records, mock Ollama responses)
├── test_agent.py            # Tests for _decide_distribution, _build_queue_record, generate_reels
├── test_prompts.py          # Tests for all format_* functions, build_generation_prompt
├── test_ollama_client.py    # Tests for generate_json parsing logic
├── test_airtable_client.py  # Tests for pagination, batching, query construction
└── test_routes.py           # FastAPI route tests using AsyncClient
```

**Fixture patterns for this codebase:**
```python
# conftest.py
import pytest

@pytest.fixture
def sample_client_record():
    return {
        "id": "recABC123",
        "fields": {
            "Client Name": "Test Client",
            "Business Info": "Test business",
            "Tone Of Voice": "Professional",
            "Niche": ["Marketing"],
            "ig_username": "testclient",
        },
    }

@pytest.fixture
def sample_magnets():
    return [
        {
            "id": "recMAG001",
            "fields": {
                "Magnet Name": "Free Guide",
                "Description": "A free guide",
                "Trigger Word": "guide",
                "Awareness Stage": "Solution-Aware",
            },
        }
    ]

@pytest.fixture
def sample_generated_reel():
    return {
        "hook": "Test hook",
        "hook_type": "שאלה מאתגרת",
        "text_on_video": "Test text",
        "verbal_script": "Test script",
        "caption": "Test caption",
        "format": "talking_head",
        "content_type": "חשיפה",
        "awareness_stage": "Unaware",
        "magnet_id": None,
    }
```

**Mocking pattern for httpx (using respx):**
```python
import respx
import httpx

@respx.mock
async def test_airtable_fetch_all():
    respx.get("https://api.airtable.com/v0/app.../TableName").mock(
        return_value=httpx.Response(200, json={
            "records": [{"id": "rec1", "fields": {"Name": "Test"}}]
        })
    )
    records = await airtable_client._fetch_all("TableName")
    assert len(records) == 1
```

## CI/CD Integration

- No CI/CD pipeline exists (no GitHub Actions, GitLab CI, or similar config)
- No Makefile or task runner for running tests
- No pre-commit hooks configured

**Recommended `Makefile` targets:**
```makefile
test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ --cov=. --cov-report=term-missing

lint:
	ruff check .

format:
	ruff format .
```

---

*Testing analysis: 2026-03-11*

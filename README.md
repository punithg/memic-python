# Memic Python SDK

Official Python SDK for the [Memic](https://memic.ai) Context Engineering API.

Upload documents, process them into searchable chunks, and perform semantic search with metadata filters.

## Installation

```bash
pip install memic
```

## Quick Start

```python
from memic import Memic, MetadataFilters, PageRange

# Initialize client (uses MEMIC_API_KEY env var if not provided)
client = Memic(api_key="mk_...")

# List projects
projects = client.list_projects()
for p in projects:
    print(f"{p.name}: {p.id}")

# Upload a file (waits for processing by default)
file = client.upload_file(
    project_id="your-project-id",
    file_path="/path/to/document.pdf",
    reference_id="lesson_123"  # Optional: for linking with external systems
)
print(f"Uploaded: {file.id}, status: {file.status}")

# Search with filters
results = client.search(
    query="key findings about climate change",
    project_id="your-project-id",
    top_k=10,
    min_score=0.7,
    filters=MetadataFilters(
        reference_id="TG_G1_Math",
        page_range=PageRange(gte=1, lte=50)
    )
)

for result in results:
    print(f"[{result.score:.2f}] {result.file_name} (p.{result.page_number})")
    print(f"  {result.content[:200]}...")
```

## Features

- **File Upload**: 3-step presigned URL flow for efficient uploads
- **Wait for Ready**: Automatic polling until file processing completes
- **Semantic Search**: Vector similarity search with rich metadata
- **Metadata Filters**: Filter by reference_id, page numbers, categories
- **Simple API**: Single client class, no complex patterns

## Configuration

### API Key

Set your API key via environment variable or constructor:

```bash
export MEMIC_API_KEY=mk_your_api_key_here
```

```python
# Or pass directly
client = Memic(api_key="mk_...")
```

### Custom Base URL

For development or self-hosted deployments:

```python
client = Memic(
    api_key="mk_...",
    base_url="https://your-api.example.com"
)
```

## API Reference

### Memic Client

```python
client = Memic(
    api_key: str = None,        # Uses MEMIC_API_KEY env var if not provided
    base_url: str = None,       # Default: https://api.memic.ai
    timeout: int = 30           # Request timeout in seconds
)
```

### Methods

#### `list_projects() -> List[Project]`

List all projects in your organization.

#### `upload_file(project_id, file_path, ...) -> File`

Upload a file to a project.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | str | required | Target project ID |
| `file_path` | str/Path | required | Path to file |
| `wait_for_ready` | bool | True | Wait for processing to complete |
| `reference_id` | str | None | External reference ID |
| `metadata` | dict | None | Custom metadata |
| `poll_interval` | float | 2.0 | Seconds between status checks |
| `poll_timeout` | float | 300 | Max wait time in seconds |

#### `get_file_status(project_id, file_id) -> File`

Get current processing status of a file.

#### `search(query, ...) -> SearchResults`

Search for content across documents.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | required | Search query |
| `project_id` | str | None | Limit to project |
| `file_ids` | List[str] | None | Limit to specific files |
| `top_k` | int | 10 | Number of results |
| `min_score` | float | 0.7 | Minimum similarity score |
| `filters` | MetadataFilters | None | Metadata filters |

### Types

#### `FileStatus`

Enum with processing states:
- `UPLOADING`, `UPLOADED`, `UPLOAD_FAILED`
- `CONVERSION_STARTED`, `CONVERSION_COMPLETE`, `CONVERSION_FAILED`
- `PARSING_STARTED`, `PARSING_COMPLETE`, `PARSING_FAILED`
- `CHUNKING_STARTED`, `CHUNKING_COMPLETE`, `CHUNKING_FAILED`
- `EMBEDDING_STARTED`, `EMBEDDING_COMPLETE`, `EMBEDDING_FAILED`
- `READY`

Properties:
- `.is_failed` - True if status indicates failure
- `.is_processing` - True if still processing

#### `MetadataFilters`

```python
MetadataFilters(
    reference_id: str = None,       # Filter by reference ID
    reference_ids: List[str] = None, # Multiple reference IDs (OR)
    page_number: int = None,        # Exact page match
    page_numbers: List[int] = None, # Multiple pages (OR)
    page_range: PageRange = None,   # Page range
    category: str = None,           # Category filter
    document_type: str = None       # Document type filter
)
```

### Exceptions

```python
from memic import MemicError, AuthenticationError, NotFoundError, APIError

try:
    results = client.search(query="test")
except AuthenticationError:
    print("Invalid API key")
except NotFoundError:
    print("Resource not found")
except APIError as e:
    print(f"API error: {e.status_code} - {e.message}")
except MemicError as e:
    print(f"Error: {e.message}")
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Type check
mypy src/memic/

# Lint
ruff check src/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

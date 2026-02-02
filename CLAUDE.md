# CLAUDE.md - Memic Python SDK

Guidelines for AI assistants working on this codebase.

## Package Overview

This is the official Python SDK for the Memic Context Engineering API. It provides:
- File uploads with presigned URLs
- Semantic search with metadata filters
- Simple, KISS-focused design

## Project Structure

```
memic-python/
├── src/memic/
│   ├── __init__.py      # Public exports
│   ├── _version.py      # Version string
│   ├── client.py        # Main Memic class
│   ├── types.py         # Pydantic models
│   └── exceptions.py    # Exception classes
└── tests/
    └── test_client.py   # Unit tests
```

## Backwards Compatibility Rules

### Semantic Versioning

- **V0.x**: Breaking changes allowed in MINOR versions (0.1 → 0.2)
- **V1.0+**: Breaking changes ONLY in MAJOR versions (1.0 → 2.0)

### What IS a Breaking Change

1. Removing or renaming public functions, classes, or methods
2. Changing function signatures (removing params, changing required/optional)
3. Changing return types
4. Changing exception types thrown by a function
5. Removing or renaming dataclass/Pydantic model fields
6. Changing default values that alter behavior

### What is NOT Breaking

1. Adding new optional parameters with defaults
2. Adding new methods, classes, or fields
3. Bug fixes that match documented behavior
4. Performance improvements
5. Adding new exception subclasses

### Deprecation Process

1. Use `warnings.warn(DeprecationWarning)` with removal version:
   ```python
   import warnings
   warnings.warn(
       "old_method() is deprecated, use new_method() instead. "
       "Will be removed in v0.3.0",
       DeprecationWarning,
       stacklevel=2
   )
   ```

2. Document in CHANGELOG with replacement

3. Minimum deprecation period:
   - 6 months OR
   - 2 minor versions (whichever is longer)

4. Add code comment: `# Deprecated: removal in vX.X`

## Design Principles (KISS)

- Single `Memic` class, no nested resource patterns
- Use `requests` for HTTP (sync only in V0.x)
- Pydantic models for types (runtime validation, IDE support)
- 4 exception classes only (MemicError, AuthenticationError, NotFoundError, APIError)
- Env var fallback for API key (MEMIC_API_KEY)

## Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=memic tests/

# Type check
mypy src/memic/
```

## Common Tasks

### Adding a New API Method

1. Add method to `client.py` in the `Memic` class
2. Add any new types to `types.py`
3. Add tests to `test_client.py`
4. Update `__init__.py` if new types need exporting
5. Update CHANGELOG.md

### Releasing a New Version

1. Update version in `src/memic/_version.py`
2. Update CHANGELOG.md with changes
3. Create git tag: `git tag v0.1.0`
4. Build: `python -m build`
5. Upload: `twine upload dist/*`

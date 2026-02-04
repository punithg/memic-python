# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-04

### Changed

- **Breaking**: Restructured search response to use nested `results` container
  - `results.semantic` - List of semantic search results (was `results`)
  - `results.structured` - Structured query results with schema metadata (was `structured_results`)
- **Breaking**: `StructuredResult` now contains `columns` and `rows` instead of `data` and `score`
  - `columns` - List of `ColumnInfo` with name, type, and description
  - `rows` - List of row dictionaries

### Added

- `ColumnInfo` model for structured result column metadata
- `ResultsContainer` model for nested semantic/structured results
- Convenience properties on `SearchResults`: `.semantic` and `.structured` shortcuts
- `StructuredResult.has_data` property to check if rows exist

## [0.1.2] - 2026-02-02

### Fixed

- Changed default base URL to production Railway endpoint with `/api/v1` prefix

## [0.1.1] - 2026-02-02

### Fixed

- Changed default base URL from `api.memic.ai` to `app.memic.ai`

## [0.1.0] - 2026-02-02

### Added

- Initial release of the Memic Python SDK
- `Memic` client class with core functionality:
  - `list_projects()` - List all projects in organization
  - `upload_file()` - Upload files with presigned URL flow
  - `get_file_status()` - Check file processing status
  - `wait_for_ready()` - Poll until file is ready
  - `search()` - Semantic search with metadata filters
- Pydantic models for type safety:
  - `Project` - Project information
  - `File` - File information with status
  - `FileStatus` - Processing status enum with `is_failed` and `is_processing` properties
  - `SearchResult` - Individual search result
  - `SearchResults` - Iterable container for search results
  - `MetadataFilters` - Filter configuration for search
  - `PageRange` - Page range filter helper
- Exception hierarchy:
  - `MemicError` - Base exception
  - `AuthenticationError` - 401/403 errors
  - `NotFoundError` - 404 errors
  - `APIError` - Other HTTP errors
- Auto-discovery of organization ID from API key
- Environment variable support (`MEMIC_API_KEY`, `MEMIC_BASE_URL`)
- User-Agent header (`memic-python/{version}`)

### Notes

- V0.x releases may contain breaking changes in minor versions
- Async client planned for V0.2
- Batch operations planned for V0.3

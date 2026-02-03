---
name: memic-sdk
description: Help developers integrate Memic's unified search API into their multi-tenant applications. Use this skill when setting up the Memic Python SDK, implementing document upload/search, or debugging integration issues.
---

# Memic SDK Integration

Help the developer integrate Memic's unified search API into their application.

## First: Understand the Use Case

**Ask the developer:** "How are you planning to use Memic?"

1. **Context tool for an AI agent** - Memic provides RAG/context for your LLM-based agent (e.g., chatbot, copilot, AI assistant)
2. **Deterministic service** - Direct API integration for search functionality in your app (no AI/LLM involved)

Based on their answer, tailor your guidance:

### If Context Tool for AI Agent:
- Emphasize how search results become context for LLM prompts
- Show how to format results for injection into system/user prompts
- Discuss chunking strategies and relevance scoring for better AI responses
- Mention `reference_id` for tracking which documents informed AI answers

### If Deterministic Service:
- Focus on direct search integration patterns
- Emphasize filtering, pagination, and result handling
- Show how to build traditional search UIs
- Discuss caching strategies for performance

## Prerequisites Check

Before starting, confirm the developer has:
- Python 3.8+
- A Memic account at https://app.memic.ai
- Access to create API keys

## Step 1: Get API Key

Guide the developer to:
1. Go to **https://app.memic.ai**
2. Log in to their account
3. Navigate to **Dashboard → API Keys**
4. Click **"Create API Key"**
5. Copy the key (starts with `mk_...`)

**Security Reminder**: This API key has full access to the organization's data. Recommend rotating the key after POC implementation.

## Step 2: Install SDK

```bash
pip install memic
```

## Step 3: Configure Environment

```bash
# Add to .env file
MEMIC_API_KEY=mk_your_api_key_here
```

Or export directly:
```bash
export MEMIC_API_KEY=mk_your_api_key_here
```

## Step 4: Multi-Tenant Architecture

Explain that in Memic, each **Project** represents one **client/tenant**:

```
Organization (1 API key)
├── Project: "Client A" → Client A's documents
├── Project: "Client B" → Client B's documents
└── Project: "Client C" → Client C's documents
```

Recommend maintaining a mapping:
```python
TENANT_PROJECTS = {
    "client_a": "uuid-of-project-a",
    "client_b": "uuid-of-project-b",
}
```

## Step 5: Core Implementation

### Initialize Client
```python
from memic import Memic

client = Memic()  # Uses MEMIC_API_KEY env var
```

### List Projects
```python
projects = client.list_projects()
for p in projects:
    print(f"{p.name}: {p.id}")
```

### Upload Documents
```python
file = client.upload_file(
    project_id="your-project-id",
    file_path="/path/to/document.pdf",
    reference_id="custom_ref_123",  # Optional
)
print(f"Status: {file.status}")  # "ready" when done
```

### Search with Filters
```python
from memic import Memic, MetadataFilters, PageRange

results = client.search(
    query="What are the key findings?",
    project_id=project_id,
    top_k=10,
    min_score=0.7,
    filters=MetadataFilters(
        reference_id="Q4_2024",
        page_range=PageRange(gte=1, lte=50),
    )
)

for result in results:
    print(f"[{result.score:.2f}] {result.file_name}: {result.content[:100]}")
```

## Use Case Specific Patterns

### Pattern A: Context Tool for AI Agent

Use Memic search results as context for your LLM:

```python
from memic import Memic, MetadataFilters
from openai import OpenAI  # or anthropic, etc.

memic = Memic()
llm = OpenAI()

def ask_with_context(user_question: str, project_id: str) -> str:
    # 1. Get relevant context from Memic
    results = memic.search(
        query=user_question,
        project_id=project_id,
        top_k=5,
        min_score=0.7,
    )

    # 2. Format context for LLM
    context = "\n\n".join([
        f"[Source: {r.file_name}, Page {r.page_number}]\n{r.content}"
        for r in results
    ])

    # 3. Generate response with context
    response = llm.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"Answer based on this context:\n\n{context}"},
            {"role": "user", "content": user_question}
        ]
    )

    return response.choices[0].message.content

# Usage
answer = ask_with_context("What are the Q4 results?", project_id="...")
```

### Pattern B: Deterministic Service

Direct integration for traditional search functionality:

```python
from memic import Memic, MetadataFilters, PageRange
from typing import List, Dict

memic = Memic()

def search_documents(
    query: str,
    tenant_id: str,
    page: int = 1,
    page_size: int = 10,
    category: str = None,
) -> Dict:
    """Search API for your application."""

    # Map tenant to Memic project
    project_id = TENANT_PROJECTS[tenant_id]

    # Build filters
    filters = None
    if category:
        filters = MetadataFilters(category=category)

    # Search with offset for pagination
    results = memic.search(
        query=query,
        project_id=project_id,
        top_k=page_size,
        min_score=0.5,  # Lower threshold for broader results
        filters=filters,
    )

    # Format response for your API
    return {
        "query": query,
        "results": [
            {
                "title": r.file_name,
                "snippet": r.content[:300],
                "page": r.page_number,
                "score": r.score,
                "file_id": r.file_id,
            }
            for r in results
        ],
        "total": results.total_results,
        "search_time_ms": results.search_time_ms,
    }
```

## Debugging Guide

### Common Issues

| Issue | Solution |
|-------|----------|
| `AuthenticationError` | Check `MEMIC_API_KEY` is set correctly |
| `NotFoundError` | Verify project_id exists in your org |
| Empty results | Check files are uploaded and status is `READY` |
| Low scores | Adjust `min_score` or rephrase query |

### Check File Status
```python
file = client.get_file_status(project_id, file_id)
print(f"Status: {file.status}")
print(f"Is processing: {file.status.is_processing}")
print(f"Is failed: {file.status.is_failed}")
if file.error_message:
    print(f"Error: {file.error_message}")
```

### Exception Handling
```python
from memic import MemicError, AuthenticationError, NotFoundError, APIError

try:
    results = client.search(query="test", project_id="...")
except AuthenticationError:
    print("Invalid API key")
except NotFoundError:
    print("Project not found")
except APIError as e:
    print(f"API error {e.status_code}: {e.message}")
```

## Security Best Practices

1. **Never commit API keys** - Use environment variables
2. **Rotate keys after POC** - Generate new production key
3. **Use project scoping** - Always specify `project_id` for tenant isolation
4. **Monitor usage** - Check dashboard for anomalies

## Resources

- SDK Repository: https://github.com/memic-ai/memic-python
- Dashboard: https://app.memic.ai
- Documentation: https://docs.memic.ai

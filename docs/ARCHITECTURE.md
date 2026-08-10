# llmwiki architecture

llmwiki is a two-service application: a React/Vite single-page app served by Nginx and a FastAPI API. Nginx is the public entry point and proxies `/api` to FastAPI with buffering disabled for SSE.

## Data boundaries

- Global data: `settings.json`, `profile/profile.json`, and `projects.json`.
- Project data: conversations, reviews, ingest caches, page history, media, and Markdown wiki pages.
- `ProjectStore` resolves a project ID to its directory. Project routes then construct `FileStore` and `WikiStore` instances rooted at that directory.

The runtime has no external database, cache, queue worker, or authentication service.

## Request flow

```text
Browser -> Nginx -> FastAPI route -> project/global store
                                |-> ChatAgent -> Wiki retrieval -> LLM adapter
                                |-> Ingest pipeline -> Markdown + JSON
                                |-> Research pipeline -> search API + LLM adapter
```

Project resources use `/api/projects/{project_id}/...`. Settings and profile are global at `/api/settings` and `/api/profile`.

Both OpenAI-compatible Chat Completions and Anthropic Messages protocols are normalized to the same internal content/reasoning stream. Browser-facing streams use SSE events named `reasoning`, `chunk`, `references`, `options`, `progress`, `done`, and `error`.

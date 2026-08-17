# llmwiki architecture

llmwiki is a two-service application: a React/Vite single-page app served by Nginx and a FastAPI API. Nginx is the public entry point and proxies `/api` to FastAPI with buffering disabled for SSE.

## Data boundaries

- Global data: `settings.json`, `profile/profile.json`, and `projects.json`.
- Project data: conversations, reviews, ingest caches/jobs, page history, media, and Markdown wiki pages.
- `ProjectStore` resolves a project ID to its directory. Project routes then reuse `FileStore` and `WikiStore` instances rooted at that directory.
- Project runtimes are reused for the application lifetime. JSON updates use in-process path locks and atomic replacement; Markdown remains the source of truth.
- `WikiStore` incrementally indexes Markdown using path/mtime/size fingerprints. Search uses the in-memory token index and can optionally blend local character similarity; graph and insight requests share a generation-based graph cache. Direct external Markdown edits are detected on the next access.
- Markdown replacements use temporary files, `fsync`, and `os.replace`. Ingest page sets snapshot every target and roll back already-touched pages when a batch commit fails.

The runtime has no external database, cache, queue worker, or authentication service.

## Request flow

```text
Browser -> Nginx -> FastAPI route -> project/global store
                                |-> ChatAgent -> Wiki retrieval -> LLM adapter
                                |-> Ingest pipeline -> persistent staging job
                                                       |-> accept -> Markdown + JSON
                                                       |-> reject -> discard staging
                                |-> Research pipeline -> search API + LLM adapter
                                                       |-> persistent job + approval
```

Project resources use `/api/projects/{project_id}/...`. Settings and profile are global at `/api/settings` and `/api/profile`.

Both OpenAI-compatible Chat Completions and Anthropic Messages protocols are normalized to the same internal content/reasoning stream. Browser-facing streams use SSE events named `reasoning`, `chunk`, `references`, `options`, `progress`, `done`, and `error`.

The same active provider configuration is used for text and image-caption requests. API keys are redacted from read responses; blank updates preserve stored keys and explicit clear flags remove them.

Ingest generation does not mutate the live Wiki. The upload and generated proposals remain under the project `ingest-jobs/` directory until accepted or rejected. Running jobs interrupted by a restart become explicitly resumable rather than being presented as successful.

Deep Research follows the same review-before-commit boundary in `research-jobs/`. Missing search configuration and zero-source searches fail closed. Review items can link to a research job and are resolved only after the generated pages are accepted and committed.

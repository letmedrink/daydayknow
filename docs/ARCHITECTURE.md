# llmwiki architecture

llmwiki is a two-service application: a React/Vite single-page app served by Nginx and a FastAPI API. Nginx is the public entry point and proxies `/api` to FastAPI with buffering disabled for SSE.

## Data boundaries

- Global data: `settings.json`, `profile/profile.json`, and `projects.json`.
- Project data: conversations, reviews, ingest/research/change jobs, page history, project Schema, immutable Raw Sources, media, and Markdown wiki pages.
- `ProjectStore` resolves a project ID to its directory. Project routes then reuse `FileStore` and `WikiStore` instances rooted at that directory.
- Project runtimes are reused for the application lifetime. JSON updates use in-process path locks and atomic replacement; Markdown remains the source of truth.
- `WikiStore` incrementally indexes Markdown using path/mtime/size fingerprints. Search uses the in-memory token index and can optionally blend local character similarity; graph and insight requests share a generation-based graph cache. Direct external Markdown edits are detected on the next access.
- Markdown replacements use temporary files, `fsync`, and `os.replace`. Ingest page sets snapshot every target and roll back already-touched pages when a batch commit fails.
- Every generated update carries the reviewed page's SHA-256. Commit rejects stale updates before writing, then deterministically rebuilds `index.md` and appends `log.md`.

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
                                |-> Query/Lint pipeline -> persistent change job
                                                       |-> preview/diff -> approval
```

Project resources use `/api/projects/{project_id}/...`. Settings and profile are global at `/api/settings` and `/api/profile`.

Both OpenAI-compatible Chat Completions and Anthropic Messages protocols are normalized to the same internal content/reasoning stream. Browser-facing streams use SSE events named `reasoning`, `chunk`, `references`, `options`, `progress`, `done`, and `error`.

The same active provider configuration is used for text and image-caption requests. API keys are redacted from read responses; blank updates preserve stored keys and explicit clear flags remove them.

Ingest generation does not mutate the live Wiki. The immutable upload remains under `raw/sources/<source_id>/`; generated proposals remain under `ingest-jobs/` until accepted or rejected. Running jobs interrupted by a restart become explicitly resumable rather than being presented as successful.

The ingest pipeline hashes the original bytes, stores a versioned deterministic extraction, analyzes every heading/character-budget chunk, then retrieves candidate pages with hybrid search. The model receives the project Schema, new evidence, and complete candidate page bodies and must return a complete target page. It cannot synthesize `index.md` or `log.md`.

Deep Research follows the same review-before-commit boundary in `research-jobs/`. Missing search configuration and zero-source searches fail closed. Review items can link to a research job and are resolved only after the generated pages are accepted and committed.

Wiki mutations are exposed as project-scoped create/update, rename, merge, delete, history and restore operations. Replacements write a version under `page-history/`; rename and merge rewrite affected wikilinks and invalidate the shared search/graph runtime.

Ingest proposals are editable and selectable before commit. Legacy jobs retain their old merge-compatible format; all new proposals explicitly use `create` or `update`. The task center reads persisted ingest, research, query-backfill and lint jobs, so review and retry state survives browser refreshes and backend restarts.

Persisted assistant messages have stable IDs. Query backfill validates the selected assistant message and preserves its question, answer, references and source IDs in an auditable change job. Wiki lint combines deterministic findings with optional model-generated findings and fixes; model fixes still require review.

Research results are canonicalized and deduplicated before use. Up to ten public HTTP(S) sources are fetched with private/link-local/loopback address rejection, readable text extraction, and stable citation identifiers. The synthesis and generation prompts preserve `[S<n>]` evidence markers.

Project archives use manifest schema version 2 and contain the complete project, including Schema and Raw Sources. Exports are assembled in a temporary ZIP rather than RAM. Imports accept versions 1 and 2, enforce entry-count and expanded-size limits, reject traversal and symlinks, and always create a new managed project.

## Project Schema and Raw Sources

`schema.json` is the machine-validated contract for language, filename policy, page types, required frontmatter, special pages, review types and automatic lint cadence. `schema.md` contains domain goals and maintenance guidance. New projects copy the default contract; existing projects receive it lazily. Changing one project never affects another, and a page type already used by live pages cannot be deleted or moved to another directory.

```text
projects/{project_id}/
├── schema.json
├── schema.md
├── raw/sources/index.json
├── raw/sources/{source_id}/metadata.json
├── raw/sources/{source_id}/original.{ext}
└── raw/sources/{source_id}/extractions/{parser_version}.md
```

`source_id` is derived from the original-byte SHA-256. Original bytes and prior extraction versions are never overwritten; rejecting a proposal does not remove evidence. New frontmatter stores source IDs, while non-resolvable historic filename strings remain visible as legacy references and are reported by lint.

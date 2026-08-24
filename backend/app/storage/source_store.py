"""Immutable, content-addressed raw source storage."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import tempfile
import threading
import time
from pathlib import Path

from .schema_store import _atomic_write

_SOURCE_RE = re.compile(r"^src_[0-9a-f]{20}$")
_LOCKS_GUARD = threading.Lock()
_SOURCE_LOCKS: dict[str, threading.RLock] = {}


class SourceStore:
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.root = self.project_dir / "raw" / "sources"
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        with _LOCKS_GUARD:
            self._lock = _SOURCE_LOCKS.setdefault(str(self.root.resolve()), threading.RLock())
        if not self.index_path.exists():
            _atomic_write(self.index_path, b"[]")

    def _read_index(self) -> list[dict]:
        with self._lock:
            try:
                data = json.loads(self.index_path.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
            except (OSError, json.JSONDecodeError):
                return []

    def _write_index(self, items: list[dict]) -> None:
        with self._lock:
            _atomic_write(self.index_path, json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"))

    @staticmethod
    def valid_id(source_id: str) -> bool:
        return bool(_SOURCE_RE.fullmatch(source_id))

    def put(self, filename: str, content: bytes, extracted_text: str, parser_version: int, extra_metadata: dict | None = None) -> dict:
        with self._lock:
            return self._put_locked(filename, content, extracted_text, parser_version, extra_metadata)

    def _put_locked(self, filename: str, content: bytes, extracted_text: str, parser_version: int, extra_metadata: dict | None = None) -> dict:
        digest = hashlib.sha256(content).hexdigest()
        source_id = f"src_{digest[:20]}"
        existing = self.get(source_id)
        if existing:
            if existing.get("sha256") != digest:
                raise RuntimeError("来源 ID 冲突")
            extraction = self.extraction_path(source_id, parser_version)
            if not extraction.exists():
                _atomic_write(extraction, extracted_text.encode("utf-8"))
            versions = sorted({*[int(value) for value in existing.get("extractionVersions", [])], parser_version})
            if versions != existing.get("extractionVersions") or int(existing.get("parserVersion", 1)) != parser_version:
                existing = {**existing, "parserVersion": parser_version, "extractionVersions": versions}
                _atomic_write(
                    self.root / source_id / "metadata.json",
                    json.dumps(existing, ensure_ascii=False, indent=2).encode("utf-8"),
                )
                items = [existing if item.get("id") == source_id else item for item in self._read_index()]
                self._write_index(items)
            return existing
        safe_suffix = Path(filename).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,10}", safe_suffix):
            safe_suffix = ".bin"
        source_dir = self.root / source_id
        source_dir.mkdir(parents=True, exist_ok=True)
        original_name = f"original{safe_suffix}"
        original_path = source_dir / original_name
        if not original_path.exists():
            _atomic_write(original_path, content)
        extraction = self.extraction_path(source_id, parser_version)
        if not extraction.exists():
            _atomic_write(extraction, extracted_text.encode("utf-8"))
        now = int(time.time() * 1000)
        metadata = {
            "id": source_id,
            "filename": Path(filename).name,
            "sha256": digest,
            "size": len(content),
            "mimeType": mimetypes.guess_type(filename)[0] or "application/octet-stream",
            "originalName": original_name,
            "parserVersion": parser_version,
            "extractionVersions": [parser_version],
            "createdAt": now,
            **(extra_metadata or {}),
        }
        _atomic_write(source_dir / "metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"))
        items = self._read_index()
        items.append(metadata)
        self._write_index(sorted(items, key=lambda item: item.get("createdAt", 0), reverse=True))
        return metadata

    def list(self) -> list[dict]:
        return self._read_index()

    def get(self, source_id: str) -> dict | None:
        if not self.valid_id(source_id):
            return None
        return next((item for item in self._read_index() if item.get("id") == source_id), None)

    def original_path(self, source_id: str) -> Path:
        metadata = self.get(source_id)
        if not metadata:
            raise FileNotFoundError("来源不存在")
        path = self.root / source_id / metadata["originalName"]
        if not path.exists():
            raise FileNotFoundError("来源原件不存在")
        return path

    def extraction_path(self, source_id: str, parser_version: int) -> Path:
        if not self.valid_id(source_id):
            raise ValueError("非法来源 ID")
        return self.root / source_id / "extractions" / f"v{parser_version}.md"

    def read_extraction(self, source_id: str, parser_version: int | None = None) -> str:
        metadata = self.get(source_id)
        if not metadata:
            raise FileNotFoundError("来源不存在")
        version = parser_version or int(metadata.get("parserVersion", 1))
        path = self.extraction_path(source_id, version)
        if not path.exists():
            raise FileNotFoundError("来源解析文本不存在")
        return path.read_text(encoding="utf-8")

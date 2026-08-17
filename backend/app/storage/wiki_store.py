"""Wiki .md 文件存储 — 读写、列表、frontmatter 解析、图谱构建、图谱洞察。

核心概念：
- Wiki 页面按类型分目录存储（entities/ concepts/ sources/ 等 9 类）
- 每页是 Markdown + YAML frontmatter，通过 [[wikilink]] 交叉引用
- 图谱实时从文件构建（无数据库缓存），边权重由 4 维信号复合评分
- 社区检测使用加权连通分量，内聚度衡量社区紧密程度
- 图谱洞察包含"意外连接"和"知识缺口"两类分析
"""

import os
import re
import os
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


# ─── Frontmatter 解析 ──────────────────────────────────────────

FM_STRICT_RE = re.compile(r"^---\s*\r?\n([\s\S]*?)\r?\n---\s*(?:\r?\n|$)")
FM_ANYWHERE_RE = re.compile(r"\n---\s*\r?\n([\s\S]*?)\r?\n---\s*(?:\r?\n|$)")
MAX_PREFIX_LINES = 6

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def parse_frontmatter(content: str) -> dict:
    """解析 markdown frontmatter，返回 {frontmatter: dict|None, body: str, rawBlock: str}。"""
    located = _locate_frontmatter(content)
    if not located:
        return {"frontmatter": None, "body": content, "rawBlock": ""}

    yaml_payload, raw_block, body = located

    try:
        parsed = yaml.safe_load(yaml_payload)
    except yaml.YAMLError:
        # 尝试修复 wikilink 列表后重试
        try:
            parsed = yaml.safe_load(_repair_wikilink_lists(yaml_payload))
        except yaml.YAMLError:
            return {"frontmatter": None, "body": body, "rawBlock": raw_block}

    if not isinstance(parsed, dict):
        return {"frontmatter": None, "body": body, "rawBlock": raw_block}

    # 标准化值
    normalized = {}
    for key, value in parsed.items():
        if isinstance(value, list):
            normalized[key] = [str(v) for v in value]
        elif value is None:
            normalized[key] = ""
        else:
            normalized[key] = str(value)

    return {"frontmatter": normalized, "body": body, "rawBlock": raw_block}


def _locate_frontmatter(content: str) -> Optional[tuple[str, str, str]]:
    """定位 frontmatter 块，返回 (yaml_payload, raw_block, body)。"""
    # 严格匹配
    m = FM_STRICT_RE.match(content)
    if m:
        return m.group(1), m.group(0), content[m.end():]

    # 宽松匹配
    m = FM_ANYWHERE_RE.search(content)
    if not m:
        return None

    open_idx = m.start() + 1  # 跳过前导 \n
    line_num = content[:open_idx].count("\n") + 1
    if line_num > MAX_PREFIX_LINES:
        return None

    raw_block = content[open_idx:open_idx + len(m.group(0)) - 1]
    body = content[open_idx + len(raw_block):]

    # 检查前缀是否是代码围栏
    prefix = content[:open_idx]
    if re.match(r"^\s*```(?:yaml|yml)?\s*\r?\n$", prefix, re.IGNORECASE):
        body = re.sub(r"^\s*```\s*(?:\r?\n|$)", "", body, count=1)

    return m.group(1), raw_block, body


def _repair_wikilink_lists(payload: str) -> str:
    """修复 frontmatter 中的 wikilink 列表格式。"""
    lines = payload.split("\n")
    repaired = []
    for line in lines:
        m = re.match(
            r'^(\s*[A-Za-z_][\w-]*\s*:\s*)(\[\[[^\]]+\]\](?:\s*,\s*\[\[[^\]]+\]\])+)\s*$',
            line,
        )
        if m:
            prefix = m.group(1)
            items = [s.strip().strip('"') for s in m.group(2).split(",") if s.strip()]
            items_str = ", ".join(f'"{item}"' for item in items)
            repaired.append(f"{prefix}[{items_str}]")
        else:
            repaired.append(line)
    return "\n".join(repaired)


def extract_wikilinks(content: str) -> list[str]:
    """从 markdown 内容中提取所有 [[wikilink]] 目标。"""
    return WIKILINK_RE.findall(content)


# ─── Wiki Store ────────────────────────────────────────────────

# 页面类型 → 子目录映射
PAGE_TYPE_DIRS = {
    "entity": "entities",
    "concept": "concepts",
    "source": "sources",
    "query": "queries",
    "comparison": "comparisons",
    "synthesis": "synthesis",
    "finding": "findings",
    "thesis": "thesis",
    "methodology": "methodology",
}

SLUG_RE = re.compile(r"[^\w一-鿿-]+")


def slugify(text: str) -> str:
    """将文本转为文件名安全的 slug。"""
    slug = SLUG_RE.sub("-", text.strip().lower())
    return slug.strip("-") or "untitled"


class WikiStore:
    """Wiki .md 文件的读写和图谱构建。"""

    def __init__(self, data_dir: str | Path):
        self.wiki_dir = Path(data_dir) / "wiki"
        self.wiki_dir.mkdir(parents=True, exist_ok=True)
        self._index_lock = threading.RLock()
        self._fingerprints: dict[str, tuple[int, int]] = {}
        self._page_cache: dict[str, dict] = {}
        self._title_index: dict[str, set[str]] = {}
        self._body_index: dict[str, set[str]] = {}
        self._generation = 0
        self._graph_generation = -1
        self._graph_cache: Optional[dict] = None

    def _safe_page_path(self, rel_path: str) -> Optional[Path]:
        """Resolve a Markdown path while preventing traversal outside wiki/."""
        root = self.wiki_dir.resolve()
        candidate = (self.wiki_dir / rel_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        return candidate if candidate.suffix == ".md" else None

    # ─── 页面读写 ──────────────────────────────────────────────

    def get_page_path(self, page_type: str, slug: str) -> Path:
        """获取页面的完整路径。"""
        subdir = PAGE_TYPE_DIRS.get(page_type, "entities")
        return self.wiki_dir / subdir / f"{slug}.md"

    def read_page(self, rel_path: str) -> Optional[dict]:
        """读取 wiki 页面，返回 {frontmatter, body, rawBlock, fullPath}。"""
        full_path = self._safe_page_path(rel_path)
        if not full_path or not full_path.exists():
            return None
        self._refresh_index()
        cached = self._page_cache.get(rel_path)
        if cached:
            return {key: value for key, value in cached.items() if not key.startswith("_")}
        return None

    def write_page(
        self,
        rel_path: str,
        frontmatter: dict,
        body: str,
        merge: bool = False,
    ) -> str:
        """写入 wiki 页面。merge=True 时合并已有 frontmatter。"""
        full_path = self._safe_page_path(rel_path)
        if not full_path:
            raise ValueError("非法 Wiki 页面路径")
        with self._index_lock:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            if merge and full_path.exists():
                existing = self.read_page(rel_path)
                if existing and existing["frontmatter"]:
                    frontmatter = _merge_frontmatter(existing["frontmatter"], frontmatter)
                    self._backup_page(rel_path, existing)
            self._atomic_write_text(full_path, _render_page(frontmatter, body))
            self._invalidate_path(rel_path)
        return rel_path

    def write_raw_page(self, rel_path: str, content: str, append: bool = False) -> str:
        """Atomically write a raw Markdown page, optionally appending to it."""
        full_path = self._safe_page_path(rel_path)
        if not full_path:
            raise ValueError("非法 Wiki 页面路径")
        with self._index_lock:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            if append and full_path.exists():
                existing = full_path.read_text(encoding="utf-8")
                content = existing.rstrip() + "\n\n" + content.strip() + "\n"
            self._atomic_write_text(full_path, content)
            self._invalidate_path(rel_path)
        return rel_path

    def commit_pages(self, pages: list[dict]) -> list[str]:
        """Commit a generated page set as one best-effort filesystem transaction.

        Every target is snapshotted before the first write. If any replacement
        fails, all previously touched pages are restored before the error escapes.
        """
        snapshots: dict[str, bytes | None] = {}
        committed: list[str] = []
        with self._index_lock:
            for page in pages:
                rel_path = page["path"]
                target = self._safe_page_path(rel_path)
                if not target:
                    raise ValueError(f"非法 Wiki 页面路径: {rel_path}")
                snapshots[rel_path] = target.read_bytes() if target.exists() else None
            try:
                for page in pages:
                    rel_path = page["path"]
                    parsed = parse_frontmatter(page["content"])
                    if parsed["frontmatter"]:
                        frontmatter = parsed["frontmatter"]
                        target = self._safe_page_path(rel_path)
                        if page.get("merge", True) and target and target.exists():
                            existing = parse_frontmatter(target.read_text(encoding="utf-8"))
                            if existing["frontmatter"]:
                                frontmatter = _merge_frontmatter(existing["frontmatter"], frontmatter)
                        content = _render_page(frontmatter, parsed["body"])
                    else:
                        target = self._safe_page_path(rel_path)
                        if page.get("merge", True) and target and target.exists():
                            content = target.read_text(encoding="utf-8").rstrip() + "\n\n" + page["content"].strip() + "\n"
                        else:
                            content = page["content"]
                    target = self._safe_page_path(rel_path)
                    assert target is not None
                    target.parent.mkdir(parents=True, exist_ok=True)
                    self._atomic_write_text(target, content)
                    committed.append(rel_path)
            except BaseException:
                for rel_path, original in snapshots.items():
                    target = self._safe_page_path(rel_path)
                    if target is None:
                        continue
                    if original is None:
                        target.unlink(missing_ok=True)
                    else:
                        self._atomic_write_bytes(target, original)
                    self._invalidate_path(rel_path)
                raise
            for rel_path in committed:
                self._invalidate_path(rel_path)
        return committed

    def snapshot_pages(self, rel_paths: list[str]) -> dict[str, bytes | None]:
        with self._index_lock:
            snapshots = {}
            for rel_path in rel_paths:
                target = self._safe_page_path(rel_path)
                if not target:
                    raise ValueError(f"非法 Wiki 页面路径: {rel_path}")
                snapshots[rel_path] = target.read_bytes() if target.exists() else None
            return snapshots

    def restore_pages(self, snapshots: dict[str, bytes | None]):
        with self._index_lock:
            for rel_path, original in snapshots.items():
                target = self._safe_page_path(rel_path)
                if target is None:
                    continue
                if original is None:
                    target.unlink(missing_ok=True)
                else:
                    self._atomic_write_bytes(target, original)
                self._invalidate_path(rel_path)

    def _atomic_write_text(self, path: Path, content: str):
        self._atomic_write_bytes(path, content.encode("utf-8"))

    @staticmethod
    def _atomic_write_bytes(path: Path, content: bytes):
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        except BaseException:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise

    def delete_page(self, rel_path: str) -> bool:
        """删除 wiki 页面。"""
        full_path = self._safe_page_path(rel_path)
        if full_path and full_path.exists():
            self._backup_page(rel_path, self.read_page(rel_path))
            full_path.unlink()
            self._invalidate_path(rel_path)
            return True
        return False

    def list_pages(self) -> list[dict]:
        """列出所有 wiki 页面，返回 [{name, path, type, title}]。"""
        self._refresh_index()
        return [dict(entry["_meta"]) for entry in self._page_cache.values()]

    def page_lookup(self) -> dict[str, dict]:
        """Return a normalized title/slug lookup used by wikilink expansion."""
        pages = self.list_pages()
        lookup = {}
        for page in pages:
            lookup[page["name"].strip().lower()] = page
            lookup[page["title"].strip().lower()] = page
        return lookup

    def build_file_tree(self) -> list[dict]:
        """构建 wiki 目录树，返回递归结构。"""
        return _build_tree(self.wiki_dir, self.wiki_dir)

    # ─── 图谱构建 ──────────────────────────────────────────────

    def build_graph(self) -> dict:
        """从 wiki 页面构建知识图谱 {nodes, edges, communities}。"""
        pages = self.list_pages()
        with self._index_lock:
            if self._graph_cache is not None and self._graph_generation == self._generation:
                return self._graph_cache
        nodes = []
        edges = []
        node_map: dict[str, dict] = {}

        # 第一遍：收集所有节点
        for page in pages:
            page_data = self._page_cache.get(page["path"])
            if not page_data:
                continue

            fm = page_data["frontmatter"] or {}
            body = page_data["body"]
            node_id = page["name"]

            if fm.get("type") == "query":
                continue

            title = fm.get("title", page["name"])
            tags = fm.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]

            sources = fm.get("sources", [])
            if isinstance(sources, str):
                sources = [sources]

            related = fm.get("related", [])
            if isinstance(related, str):
                related = [related]

            node = {
                "id": node_id,
                "title": title,
                "type": fm.get("type", "other"),
                "tags": tags,
                "path": page["path"],
                "sources": sources,
                "linkCount": 0,
                "_body": body,
                "_related": related,
            }
            nodes.append(node)
            node_map[node_id] = node

        # 构建标题→ID 映射（支持中文标题匹配）
        title_to_id: dict[str, str] = {}
        for n in nodes:
            title_to_id[n["title"].strip().lower()] = n["id"]
            title_to_id[n["id"].strip().lower()] = n["id"]

        # 第二遍：提取边 + 计算出/入度
        raw_edges = []
        out_links: dict[str, set[str]] = {n["id"]: set() for n in nodes}
        in_links: dict[str, set[str]] = {n["id"]: set() for n in nodes}

        for node in nodes:
            # 从 [[wikilink]] 提取
            links = extract_wikilinks(node["_body"])
            # 从 frontmatter related 字段提取
            related = node.get("_related", [])
            if isinstance(related, str):
                related = [related]
            links.extend(related)

            for target in links:
                target_id = _resolve_link(target, title_to_id)
                if target_id and target_id in node_map and target_id != node["id"]:
                    raw_edges.append((node["id"], target_id))
                    out_links[node["id"]].add(target_id)
                    in_links[target_id].add(node["id"])

        # 去重边 + 计算权重
        seen = set()
        for src, tgt in raw_edges:
            key = tuple(sorted([src, tgt]))
            if key in seen:
                continue
            seen.add(key)
            weight = _calc_edge_weight(src, tgt, out_links, in_links, node_map)
            edges.append({
                "source": src,
                "target": tgt,
                "type": "wikilink",
                "weight": round(weight, 2),
            })

        # 设置 linkCount
        for n in nodes:
            n["linkCount"] = len(out_links[n["id"]]) + len(in_links[n["id"]])
            del n["_body"]

        # 社区检测
        communities = _detect_communities_weighted(nodes, edges)

        # 计算 maxLinks 用于前端缩放
        max_links = max((n["linkCount"] for n in nodes), default=1)

        graph = {
            "nodes": nodes,
            "edges": edges,
            "communities": communities,
            "maxLinks": max_links,
        }
        with self._index_lock:
            self._graph_cache = graph
            self._graph_generation = self._generation
        return graph

    def graph_insights(self) -> dict:
        """生成图谱洞察：Surprising Connections + Knowledge Gaps。"""
        graph = self.build_graph()
        nodes = graph["nodes"]
        edges = graph["edges"]
        communities = graph["communities"]

        node_map = {n["id"]: n for n in nodes}
        comm_map: dict[str, int] = {}
        for c in communities:
            for nid in c["nodes"]:
                comm_map[nid] = c["id"]

        # 构建邻接表
        adj: dict[str, set[str]] = {n["id"]: set() for n in nodes}
        for e in edges:
            adj[e["source"]].add(e["target"])
            adj[e["target"]].add(e["source"])

        surprising = _find_surprising_connections(nodes, edges, comm_map, node_map, adj)
        gaps = _detect_knowledge_gaps(nodes, edges, communities, comm_map, adj)

        return {
            "surprisingConnections": surprising,
            "knowledgeGaps": gaps,
        }

    # ─── 搜索 ──────────────────────────────────────────────────

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        """分词搜索 wiki 页面标题和内容。"""
        query_lower = query.lower()
        # 简单分词：按空格和中文字符
        tokens = _tokenize(query_lower)
        if not tokens:
            return []

        self._refresh_index()
        candidates: set[str] = set()
        for token in tokens:
            candidates.update(self._title_index.get(token, set()))
            candidates.update(self._body_index.get(token, set()))

        results = []
        for path in candidates:
            page_data = self._page_cache.get(path)
            if not page_data:
                continue
            page = page_data["_meta"]
            title_lower = page["title"].lower()
            body_lower = page_data["body"].lower()
            combined = title_lower + " " + body_lower

            # 计算匹配分数
            score = 0
            for token in tokens:
                if token in title_lower:
                    score += 3  # 标题匹配权重更高
                if token in body_lower:
                    score += 1

            if score > 0:
                results.append({
                    **page,
                    "score": score,
                    "snippet": _extract_snippet(page_data["body"], tokens),
                })

        results.sort(key=lambda r: r["score"], reverse=True)
        # 过滤低相关度：至少匹配 2 分（1 个 bigram 标题=3，1 个 bigram 正文=1）
        return [r for r in results if r["score"] >= 2][:max_results]

    def hybrid_search(self, query: str, max_results: int = 10) -> list[dict]:
        """Combine exact inverted-index matches with local character similarity."""
        self._refresh_index()
        lexical = {item["path"]: item for item in self.search(query, max_results=max_results * 2)}
        query_grams = _character_ngrams(query)
        scored = []
        for path, page_data in self._page_cache.items():
            meta = page_data["_meta"]
            title_similarity = _dice_similarity(query_grams, _character_ngrams(str(meta["title"])))
            body_similarity = _dice_similarity(query_grams, _character_ngrams(page_data["body"][:4000]))
            lexical_score = float(lexical.get(path, {}).get("score", 0))
            score = lexical_score + title_similarity * 6 + body_similarity * 2
            if lexical_score <= 0 and title_similarity < 0.18 and body_similarity < 0.08:
                continue
            scored.append({
                **meta,
                "score": round(score, 4),
                "snippet": lexical.get(path, {}).get("snippet") or _extract_snippet(page_data["body"], list(query_grams)),
            })
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:max_results]

    # ─── 内部方法 ──────────────────────────────────────────────

    def _backup_page(self, rel_path: str, page_data: Optional[dict]):
        """备份页面到 page-history/。"""
        if not page_data:
            return
        backup_dir = self.wiki_dir.parent / "page-history"
        backup_dir.mkdir(parents=True, exist_ok=True)
        safe_name = rel_path.replace("/", "_").replace("\\", "_")
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        backup_path = backup_dir / f"{safe_name}-{ts}.md"
        content = page_data.get("rawBlock", "") + page_data.get("body", "")
        backup_path.write_text(content, encoding="utf-8")

    def _invalidate_path(self, rel_path: str):
        with self._index_lock:
            self._fingerprints.pop(rel_path, None)
            self._remove_cached_page(rel_path)
            self._generation += 1
            self._graph_cache = None

    def _remove_cached_page(self, rel_path: str):
        old = self._page_cache.pop(rel_path, None)
        if not old:
            return
        for token in old.get("_title_tokens", set()):
            paths = self._title_index.get(token)
            if paths:
                paths.discard(rel_path)
                if not paths:
                    self._title_index.pop(token, None)
        for token in old.get("_body_tokens", set()):
            paths = self._body_index.get(token)
            if paths:
                paths.discard(rel_path)
                if not paths:
                    self._body_index.pop(token, None)

    def _refresh_index(self):
        """Incrementally refresh cached pages from path/mtime/size fingerprints."""
        with self._index_lock:
            current: dict[str, tuple[Path, tuple[int, int]]] = {}
            for md_file in self.wiki_dir.rglob("*.md"):
                rel = md_file.relative_to(self.wiki_dir)
                if len(rel.parts) < 2 or _dir_to_type(rel.parts[0]) is None:
                    continue
                stat = md_file.stat()
                current[str(rel)] = (md_file, (stat.st_mtime_ns, stat.st_size))

            changed = False
            for rel_path in set(self._fingerprints) - set(current):
                self._fingerprints.pop(rel_path, None)
                self._remove_cached_page(rel_path)
                changed = True

            for rel_path, (md_file, fingerprint) in current.items():
                if self._fingerprints.get(rel_path) == fingerprint:
                    continue
                self._remove_cached_page(rel_path)
                content = md_file.read_text(encoding="utf-8")
                parsed = parse_frontmatter(content)
                rel = Path(rel_path)
                frontmatter = parsed["frontmatter"] or {}
                title = frontmatter.get("title") or md_file.stem
                meta = {
                    "name": md_file.stem,
                    "path": rel_path,
                    "type": _dir_to_type(rel.parts[0]),
                    "title": title,
                }
                title_tokens = set(_tokenize(str(title).lower()))
                body_tokens = set(_tokenize(parsed["body"].lower()))
                entry = {
                    **parsed,
                    "fullPath": str(md_file),
                    "relPath": rel_path,
                    "_meta": meta,
                    "_title_tokens": title_tokens,
                    "_body_tokens": body_tokens,
                }
                self._page_cache[rel_path] = entry
                self._fingerprints[rel_path] = fingerprint
                for token in title_tokens:
                    self._title_index.setdefault(token, set()).add(rel_path)
                for token in body_tokens:
                    self._body_index.setdefault(token, set()).add(rel_path)
                changed = True

            if changed:
                self._generation += 1
                self._graph_cache = None


def _merge_frontmatter(old: dict, new: dict) -> dict:
    """合并 frontmatter：数组取并集，标量取新值。"""
    merged = dict(old)
    for key, value in new.items():
        if key in merged and isinstance(merged[key], list) and isinstance(value, list):
            merged[key] = list(set(merged[key] + value))
        else:
            merged[key] = value
    # 更新时间戳
    merged["updated"] = datetime.now().strftime("%Y-%m-%d")
    return merged


def _render_page(frontmatter: dict, body: str) -> str:
    fm_lines = ["---"]
    for key, value in frontmatter.items():
        if isinstance(value, list):
            fm_lines.append(f"{key}:")
            fm_lines.extend(f"  - {item}" for item in value)
        else:
            fm_lines.append(f"{key}: {value}")
    fm_lines.append("---")
    return "\n".join(fm_lines) + "\n\n" + body.strip() + "\n"


def _dir_to_type(dir_name: str) -> Optional[str]:
    """子目录名反查页面类型。"""
    for t, d in PAGE_TYPE_DIRS.items():
        if d == dir_name:
            return t
    return None


def _normalize_link(text: str) -> str:
    """标准化 wikilink 目标用于匹配。"""
    return text.strip().lower().replace(" ", "-").replace("_", "-")


def _resolve_link(text: str, title_to_id: dict[str, str]) -> Optional[str]:
    """解析 wikilink 目标，支持 ID 匹配和标题匹配。"""
    normalized = _normalize_link(text)
    # 先尝试直接 ID 匹配
    if normalized in title_to_id:
        return title_to_id[normalized]
    # 再尝试标题匹配（中文 wikilink）
    title_key = text.strip().lower()
    if title_key in title_to_id:
        return title_to_id[title_key]
    return None


def _build_tree(root: Path, current: Path) -> list[dict]:
    """递归构建目录树。"""
    items = []
    if not current.exists():
        return items
    for entry in sorted(current.iterdir(), key=lambda e: (not e.is_dir(), e.name)):
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            children = _build_tree(root, entry)
            if children:
                items.append({
                    "name": entry.name,
                    "path": str(entry.relative_to(root)),
                    "is_dir": True,
                    "children": children,
                })
        elif entry.suffix == ".md":
            items.append({
                "name": entry.stem,
                "path": str(entry.relative_to(root)),
                "is_dir": False,
            })
    return items


def _tokenize(text: str) -> list[str]:
    """简单分词：英文按空格，中文按 bigram（跳过单字避免噪声）。"""
    tokens = []
    # 英文单词
    for word in re.findall(r"[a-z0-9]+", text):
        if len(word) >= 2:
            tokens.append(word)
    # 中文字符 bigram（足够匹配词义，避免单字噪声）
    cn_chars = re.findall(r"[一-鿿]", text)
    for i in range(len(cn_chars) - 1):
        tokens.append(cn_chars[i] + cn_chars[i + 1])
    return tokens


def _character_ngrams(text: str, size: int = 2) -> set[str]:
    normalized = re.sub(r"\s+", "", text.lower())
    if not normalized:
        return set()
    if len(normalized) <= size:
        return {normalized}
    return {normalized[index:index + size] for index in range(len(normalized) - size + 1)}


def _dice_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return 2 * len(left & right) / (len(left) + len(right))


def _extract_snippet(body: str, tokens: list[str], context_chars: int = 100) -> str:
    """提取包含搜索词的片段。"""
    body_lower = body.lower()
    for token in tokens:
        idx = body_lower.find(token)
        if idx >= 0:
            start = max(0, idx - context_chars)
            end = min(len(body), idx + len(token) + context_chars)
            snippet = body[start:end].strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(body):
                snippet = snippet + "..."
            return snippet
    return body[:200].strip() + ("..." if len(body) > 200 else "")


def _calc_edge_weight(
    src: str, tgt: str,
    out_links: dict[str, set[str]],
    in_links: dict[str, set[str]],
    node_map: dict[str, dict],
) -> float:
    """计算边权重：4 信号复合评分。

    信号说明：
    1. 直接 [[wikilink]] 链接 — 基础分 3.0（必然存在，因为边由此产生）
    2. 共享来源文档 — 每共享一个来源 +4.0（最强信号，同一文档引出的概念关联度高）
    3. Adamic-Adar 共同邻居 — 共邻度 / √deg，压低大度节点的噪声
    4. 类型亲和度 — 预设类型组合的加分（entity↔concept, finding↔thesis 等）
    """
    score = 0.0

    # 信号 1：直接链接（基础分）
    score += 3.0

    # 信号 2：共享来源文档（每共享一个 +4.0）
    src_sources = set(node_map.get(src, {}).get("sources", []))
    tgt_sources = set(node_map.get(tgt, {}).get("sources", []))
    if src_sources and tgt_sources:
        shared = len(src_sources & tgt_sources)
        score += shared * 4.0

    # 信号 3：Adamic-Adar 共邻（log 阻尼大度节点）
    src_neighbors = out_links.get(src, set()) | in_links.get(src, set())
    tgt_neighbors = out_links.get(tgt, set()) | in_links.get(tgt, set())
    common = src_neighbors & tgt_neighbors
    if common:
        for c in common:
            deg = len(out_links.get(c, set()) | in_links.get(c, set()))
            if deg > 1:
                score += 1.5 / (deg ** 0.5)

    # 信号 4：类型亲和度（预设类型组合加分）
    type_affinity = {
        ("entity", "concept"): 1.2,
        ("concept", "entity"): 1.2,
        ("source", "entity"): 1.1,
        ("entity", "source"): 1.1,
        ("finding", "thesis"): 1.3,
        ("thesis", "finding"): 1.3,
        ("comparison", "entity"): 1.1,
        ("entity", "comparison"): 1.1,
    }
    src_type = node_map.get(src, {}).get("type", "other")
    tgt_type = node_map.get(tgt, {}).get("type", "other")
    score += type_affinity.get((src_type, tgt_type), 1.0)

    return score


def _detect_communities_weighted(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """加权连通分量社区检测。

    算法步骤：
    1. 构建邻接表（无向图）
    2. BFS 找出所有连通分量（每个分量 = 一个社区）
    3. 计算每个社区的内聚度（cohesion）——实际边数 / 最大可能边数
    4. 按社区大小降序排列，top-5 节点作为社区代表
    """
    # 构建邻接表（无向图）
    adj: dict[str, set[str]] = {}
    for n in nodes:
        adj[n["id"]] = set()
    for e in edges:
        adj.setdefault(e["source"], set()).add(e["target"])
        adj.setdefault(e["target"], set()).add(e["source"])

    visited = set()
    communities = []
    node_map = {n["id"]: n for n in nodes}

    # BFS 找连通分量
    for n in nodes:
        nid = n["id"]
        if nid in visited:
            continue
        component = []
        queue = [nid]
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            component.append(curr)
            for neighbor in adj.get(curr, set()):
                if neighbor not in visited:
                    queue.append(neighbor)
        if not component:
            continue

        # 计算内聚度：社区内部实际边数 / 最大可能边数
        intra_edges = 0
        for e in edges:
            if e["source"] in set(component) and e["target"] in set(component):
                intra_edges += 1
        n_nodes = len(component)
        max_possible = n_nodes * (n_nodes - 1) / 2 if n_nodes > 1 else 1
        cohesion = round(intra_edges / max_possible, 3) if max_possible > 0 else 0

        # 取社区内 linkCount top-5 节点作为代表
        comp_nodes = [(nid, node_map.get(nid, {}).get("linkCount", 0)) for nid in component]
        comp_nodes.sort(key=lambda x: x[1], reverse=True)
        top_nodes = [nid for nid, _ in comp_nodes[:5]]

        communities.append({
            "id": len(communities),
            "nodes": component,
            "size": len(component),
            "cohesion": cohesion,
            "topNodes": top_nodes,
        })

    # 按社区大小降序排序，重新编号
    communities.sort(key=lambda c: c["size"], reverse=True)
    for i, c in enumerate(communities):
        c["id"] = i

    return communities
def _find_surprising_connections(
    nodes: list[dict],
    edges: list[dict],
    comm_map: dict[str, int],
    node_map: dict[str, dict],
    adj: dict[str, set[str]],
) -> list[dict]:
    """发现跨社区/跨类型的意外连接。

    评分规则：
    - 跨社区连接：+3（不同社区间有边，意味着潜在的知识融合点）
    - 跨类型连接：+1~2（entity↔concept 额外 +1）
    - 桥接节点连接：+2（至少一端连接 3+ 社区）
    - 返回 score ≥ 3 的连接，按分数降序，最多 10 条
    """
    scored = []

    for e in edges:
        src, tgt = e["source"], e["target"]
        src_comm = comm_map.get(src, -1)
        tgt_comm = comm_map.get(tgt, -1)
        src_type = node_map.get(src, {}).get("type", "other")
        tgt_type = node_map.get(tgt, {}).get("type", "other")

        score = 0
        reasons = []

        # 跨社区连接
        if src_comm != tgt_comm and src_comm >= 0 and tgt_comm >= 0:
            score += 3
            reasons.append("跨社区")

        # 跨类型连接
        if src_type != tgt_type:
            score += 1
            if (src_type, tgt_type) in {("entity", "concept"), ("concept", "entity")}:
                score += 1
            reasons.append("跨类型")

        # 桥接节点（连接 3+ 社区的节点）
        for nid in [src, tgt]:
            neighbor_comms = set()
            for nb in adj.get(nid, set()):
                nc = comm_map.get(nb, -1)
                if nc >= 0:
                    neighbor_comms.add(nc)
            if len(neighbor_comms) >= 3:
                score += 2
                reasons.append(f"桥接节点({nid})")
                break

        if score >= 3:
            scored.append({
                "source": src,
                "target": tgt,
                "sourceTitle": node_map.get(src, {}).get("title", src),
                "targetTitle": node_map.get(tgt, {}).get("title", tgt),
                "score": score,
                "reasons": reasons,
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:10]


def _detect_knowledge_gaps(
    nodes: list[dict],
    edges: list[dict],
    communities: list[dict],
    comm_map: dict[str, int],
    adj: dict[str, set[str]],
) -> list[dict]:
    """检测三类知识缺口。

    1. 孤立节点：度 ≤ 1，缺少交叉引用，建议深入研究
    2. 稀疏社区：≥3 个节点但内聚度 < 0.15，内部连接不足
    3. 桥接节点：连接 3+ 社区，扩展它能增强整个知识网络
    """
    gaps = []
    node_map = {n["id"]: n for n in nodes}

    for n in nodes:
        nid = n["id"]
        degree = len(adj.get(nid, set()))

        # 孤立节点（度 <= 1）
        if degree <= 1:
            gaps.append({
                "type": "isolated",
                "nodeId": nid,
                "title": n["title"],
                "nodeType": n["type"],
                "suggestion": f"「{n['title']}」连接较少，考虑添加 [[wikilink]] 或深入研究以扩展内容。",
                "searchQuery": n["title"],
            })

    # 稀疏社区（内聚度 < 0.15）
    for c in communities:
        if c["cohesion"] < 0.15 and c["size"] >= 3:
            top_titles = [node_map.get(nid, {}).get("title", nid) for nid in c["topNodes"][:3]]
            gaps.append({
                "type": "sparse_community",
                "communityId": c["id"],
                "size": c["size"],
                "topNodes": c["topNodes"],
                "suggestion": f"社区 {c['id']}（{', '.join(top_titles)}...）内部连接稀疏，考虑补充交叉引用。",
                "searchQuery": " ".join(top_titles),
            })

    # 桥接节点（连接 3+ 社区）
    for n in nodes:
        nid = n["id"]
        neighbor_comms = set()
        for nb in adj.get(nid, set()):
            nc = comm_map.get(nb, -1)
            if nc >= 0:
                neighbor_comms.add(nc)
        if len(neighbor_comms) >= 3:
            gaps.append({
                "type": "bridge",
                "nodeId": nid,
                "title": n["title"],
                "nodeType": n["type"],
                "connectedCommunities": len(neighbor_comms),
                "suggestion": f"「{n['title']}」是桥接节点（连接 {len(neighbor_comms)} 个社区），扩展它可以增强整个知识网络。",
                "searchQuery": n["title"],
            })

    return gaps


def _detect_communities(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """简单的连通分量社区检测（保留兼容）。"""
    return _detect_communities_weighted(nodes, edges)

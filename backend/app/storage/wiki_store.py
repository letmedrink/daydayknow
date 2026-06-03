"""Wiki .md 文件存储 — 读写、列表、frontmatter 解析、图谱构建。"""

import os
import re
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

    # ─── 页面读写 ──────────────────────────────────────────────

    def get_page_path(self, page_type: str, slug: str) -> Path:
        """获取页面的完整路径。"""
        subdir = PAGE_TYPE_DIRS.get(page_type, "entities")
        return self.wiki_dir / subdir / f"{slug}.md"

    def read_page(self, rel_path: str) -> Optional[dict]:
        """读取 wiki 页面，返回 {frontmatter, body, rawBlock, fullPath}。"""
        full_path = self.wiki_dir / rel_path
        if not full_path.exists() or not full_path.suffix == ".md":
            return None
        content = full_path.read_text(encoding="utf-8")
        result = parse_frontmatter(content)
        result["fullPath"] = str(full_path)
        result["relPath"] = rel_path
        return result

    def write_page(
        self,
        rel_path: str,
        frontmatter: dict,
        body: str,
        merge: bool = False,
    ) -> str:
        """写入 wiki 页面。merge=True 时合并已有 frontmatter。"""
        full_path = self.wiki_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if merge and full_path.exists():
            existing = self.read_page(rel_path)
            if existing and existing["frontmatter"]:
                frontmatter = _merge_frontmatter(existing["frontmatter"], frontmatter)
                # 备份旧文件
                self._backup_page(rel_path, existing)

        # 构建 frontmatter
        fm_lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, list):
                fm_lines.append(f"{key}:")
                for item in value:
                    fm_lines.append(f"  - {item}")
            else:
                fm_lines.append(f"{key}: {value}")
        fm_lines.append("---")

        content = "\n".join(fm_lines) + "\n\n" + body.strip() + "\n"
        full_path.write_text(content, encoding="utf-8")
        return rel_path

    def delete_page(self, rel_path: str) -> bool:
        """删除 wiki 页面。"""
        full_path = self.wiki_dir / rel_path
        if full_path.exists():
            self._backup_page(rel_path, self.read_page(rel_path))
            full_path.unlink()
            return True
        return False

    def list_pages(self) -> list[dict]:
        """列出所有 wiki 页面，返回 [{name, path, type, title}]。"""
        pages = []
        for md_file in self.wiki_dir.rglob("*.md"):
            rel = md_file.relative_to(self.wiki_dir)
            parts = rel.parts
            if len(parts) < 2:
                continue
            page_type_dir = parts[0]
            page_type = _dir_to_type(page_type_dir)
            if page_type is None:
                continue

            content = md_file.read_text(encoding="utf-8")
            result = parse_frontmatter(content)
            title = md_file.stem
            if result["frontmatter"] and result["frontmatter"].get("title"):
                title = result["frontmatter"]["title"]

            pages.append({
                "name": md_file.stem,
                "path": str(rel),
                "type": page_type,
                "title": title,
            })
        return pages

    def build_file_tree(self) -> list[dict]:
        """构建 wiki 目录树，返回递归结构。"""
        return _build_tree(self.wiki_dir, self.wiki_dir)

    # ─── 图谱构建 ──────────────────────────────────────────────

    def build_graph(self) -> dict:
        """从 wiki 页面构建知识图谱 {nodes, edges, communities}。"""
        pages = self.list_pages()
        nodes = []
        edges = []
        node_map: dict[str, dict] = {}

        # 第一遍：收集所有节点
        for page in pages:
            page_data = self.read_page(page["path"])
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

        return {
            "nodes": nodes,
            "edges": edges,
            "communities": communities,
            "maxLinks": max_links,
        }

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

        results = []
        for page in self.list_pages():
            page_data = self.read_page(page["path"])
            if not page_data:
                continue

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
        return results[:max_results]

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
    """简单分词：英文按空格，中文按字符（bigram）。"""
    tokens = []
    # 英文单词
    for word in re.findall(r"[a-z0-9]+", text):
        if len(word) >= 2:
            tokens.append(word)
    # 中文字符 bigram
    cn_chars = re.findall(r"[一-鿿]", text)
    for i in range(len(cn_chars) - 1):
        tokens.append(cn_chars[i] + cn_chars[i + 1])
    # 单个中文字符也作为 token
    for ch in cn_chars:
        tokens.append(ch)
    return tokens


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
    """计算边权重：4 信号复合评分。"""
    score = 0.0

    # 1. 直接链接（必然存在，基础分）
    score += 3.0

    # 2. 共享来源文档
    src_sources = set(node_map.get(src, {}).get("sources", []))
    tgt_sources = set(node_map.get(tgt, {}).get("sources", []))
    if src_sources and tgt_sources:
        shared = len(src_sources & tgt_sources)
        score += shared * 4.0

    # 3. Adamic-Adar 共邻
    src_neighbors = out_links.get(src, set()) | in_links.get(src, set())
    tgt_neighbors = out_links.get(tgt, set()) | in_links.get(tgt, set())
    common = src_neighbors & tgt_neighbors
    if common:
        for c in common:
            deg = len(out_links.get(c, set()) | in_links.get(c, set()))
            if deg > 1:
                score += 1.5 / (deg ** 0.5)

    # 4. 类型亲和度
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
    """加权连通分量社区检测（带内聚度和 top 节点统计）。"""
    adj: dict[str, set[str]] = {}
    for n in nodes:
        adj[n["id"]] = set()
    for e in edges:
        adj.setdefault(e["source"], set()).add(e["target"])
        adj.setdefault(e["target"], set()).add(e["source"])

    visited = set()
    communities = []
    node_map = {n["id"]: n for n in nodes}

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

        # 计算内聚度
        intra_edges = 0
        for e in edges:
            if e["source"] in set(component) and e["target"] in set(component):
                intra_edges += 1
        n_nodes = len(component)
        max_possible = n_nodes * (n_nodes - 1) / 2 if n_nodes > 1 else 1
        cohesion = round(intra_edges / max_possible, 3) if max_possible > 0 else 0

        # Top 节点（按 linkCount 排序）
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

    # 按 size 降序排序，重新编号
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
    """发现跨社区/跨类型的意外连接。"""
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
    """检测知识缺口：孤立节点、稀疏社区、桥接节点。"""
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

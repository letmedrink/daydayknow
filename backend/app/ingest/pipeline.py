"""摄入 Pipeline — 主流程编排 + FILE/REVIEW 块解析。"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import settings
from ..storage import FileStore, WikiStore
from ..storage.wiki_store import slugify, parse_frontmatter
from ..llm import call_llm
from .file_parser import parse_file
from .image_extractor import extract_images
from .image_caption import caption_images
from .prompts import build_analysis_prompt, build_generation_prompt

import logging
log = logging.getLogger("ingest")


# ─── FILE/REVIEW 块解析 ──────────────────────────────────────

OPENER_RE = re.compile(r"^---\s*FILE:\s*(.+?)\s*---\s*$", re.IGNORECASE)
CLOSER_RE = re.compile(r"^---\s*END\s+FILE\s*---\s*$", re.IGNORECASE)
FENCE_RE = re.compile(r"^\s{0,3}(```+|~~~+)")
REVIEW_RE = re.compile(
    r"---REVIEW:\s*(\w[\w-]*)\s*\|\s*(.+?)\s*---\n([\s\S]*?)---END REVIEW---",
    re.MULTILINE,
)


def parse_file_blocks(text: str) -> tuple[list[dict], list[str]]:
    """解析 FILE 块。返回 (blocks, warnings)。

    每个 block: {path: str, content: str}
    """
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")

    blocks = []
    warnings = []
    i = 0

    while i < len(lines):
        m = OPENER_RE.match(lines[i])
        if not m:
            i += 1
            continue

        path = m.group(1).strip()
        i += 1

        content_lines = []
        fence_marker = None
        fence_len = 0
        closed = False

        while i < len(lines):
            line = lines[i]

            # 更新围栏状态
            fm = FENCE_RE.match(line)
            if fm:
                run = fm.group(1)
                char = run[0]
                length = len(run)
                if fence_marker is None:
                    fence_marker = char
                    fence_len = length
                elif char == fence_marker and length >= fence_len:
                    fence_marker = None
                    fence_len = 0
                content_lines.append(line)
                i += 1
                continue

            # 在围栏外遇到 END FILE 才算关闭
            if fence_marker is None and CLOSER_RE.match(line):
                closed = True
                i += 1
                break

            content_lines.append(line)
            i += 1

        if not closed:
            label = path or "(unnamed)"
            msg = f'FILE 块 "{label}" 未关闭（可能截断）。已丢弃。'
            log.warning(msg)
            warnings.append(msg)
            continue

        if not path:
            msg = "FILE 块路径为空，已跳过。"
            log.warning(msg)
            warnings.append(msg)
            continue

        if not _is_safe_path(path):
            msg = f'FILE 块路径 "{path}" 不安全，已拒绝。'
            log.warning(msg)
            warnings.append(msg)
            continue

        blocks.append({"path": path, "content": "\n".join(content_lines)})

    return blocks, warnings


def parse_review_blocks(text: str, source_path: str = "") -> list[dict]:
    """解析 REVIEW 块。返回审阅项列表。"""
    items = []

    for m in REVIEW_RE.finditer(text):
        raw_type = m.group(1).strip().lower()
        title = m.group(2).strip()
        body = m.group(3).strip()

        valid_types = {"contradiction", "duplicate", "missing-page", "suggestion"}
        review_type = raw_type if raw_type in valid_types else "suggestion"

        # 解析 OPTIONS
        opt_m = re.search(r"^OPTIONS:\s*(.+)$", body, re.MULTILINE)
        options = []
        if opt_m:
            for o in opt_m.group(1).split("|"):
                label = o.strip()
                options.append({"label": label, "action": label})
        else:
            options = [
                {"label": "创建页面", "action": "创建页面"},
                {"label": "跳过", "action": "跳过"},
            ]

        # 解析 PAGES
        pages_m = re.search(r"^PAGES:\s*(.+)$", body, re.MULTILINE)
        affected_pages = []
        if pages_m:
            affected_pages = [p.strip() for p in pages_m.group(1).split(",") if p.strip()]

        # 解析 SEARCH
        search_m = re.search(r"^SEARCH:\s*(.+)$", body, re.MULTILINE)
        search_queries = []
        if search_m:
            search_queries = [q.strip() for q in search_m.group(1).split("|") if q.strip()]

        # 描述 = body 去掉 OPTIONS/PAGES/SEARCH 行
        description = body
        description = re.sub(r"^OPTIONS:.*$", "", description, flags=re.MULTILINE)
        description = re.sub(r"^PAGES:.*$", "", description, flags=re.MULTILINE)
        description = re.sub(r"^SEARCH:.*$", "", description, flags=re.MULTILINE)
        description = description.strip()

        items.append({
            "type": review_type,
            "title": title,
            "description": description,
            "sourcePath": source_path,
            "affectedPages": affected_pages,
            "searchQueries": search_queries,
            "options": options,
        })

    return items


def _is_safe_path(path: str) -> bool:
    """检查路径是否安全（必须在 wiki/ 下，无 .. 和绝对路径）。"""
    if not path.startswith("wiki/"):
        return False
    if ".." in path:
        return False
    if path.startswith("/") or (len(path) > 1 and path[1] == ":"):
        return False
    return True


# ─── 主流程 ──────────────────────────────────────────────────

async def run_ingest_pipeline(
    filename: str,
    content: bytes,
    file_store: FileStore,
    wiki_store: WikiStore,
    progress_callback=None,
) -> dict:
    """执行完整的摄入流程。

    Args:
        filename: 原始文件名
        content: 文件二进制内容
        file_store: 文件存储
        wiki_store: wiki 存储
        progress_callback: 进度回调 async (step, progress, message) -> None

    Returns:
        {files_written: list[str], reviews: list[dict], warnings: list[str]}
    """
    async def report(step: str, progress: float, message: str):
        log.info(f"[{step}] {message}")
        if progress_callback:
            await progress_callback(step, progress, message)

    # Step 0: 解析文件
    await report("parse", 0.0, f"正在解析文件: {filename}")
    source_content = parse_file(filename, content)

    if source_content.startswith("[") and source_content.endswith("]"):
        return {"files_written": [], "reviews": [], "warnings": [source_content]}

    # Step 1: 缓存检查
    await report("cache", 0.1, "检查缓存...")
    cached = file_store.check_ingest_cache(filename, source_content)
    if cached:
        await report("cache", 1.0, "文件未变化，跳过摄入")
        return {"files_written": cached, "reviews": [], "warnings": [], "cached": True}

    # Step 2: 图片提取
    await report("images", 0.15, "提取嵌入图片...")
    source_slug = slugify(filename.rsplit(".", 1)[0] if "." in filename else filename)
    media_dir = Path(settings.DATA_DIR) / "wiki" / "media" / source_slug
    images = extract_images(filename, content, media_dir)

    # Step 3: 图片描述
    if images:
        await report("images", 0.2, f"生成 {len(images)} 张图片的描述...")
        images = await caption_images(images, file_store)

    # 注入图片描述到源内容
    if images:
        source_content = _inject_image_descriptions(source_content, images)

    # Step 4: 构建 wiki 索引
    pages = wiki_store.list_pages()
    index_lines = []
    for p in pages:
        index_lines.append(f"- [{p['title']}] {p['path']}")
    index = "\n".join(index_lines) if index_lines else "(知识库为空)"

    # Step 5: LLM 分析
    await report("analyze", 0.25, "LLM 分析文档内容...")
    analysis = await call_llm(
        file_store,
        "你是一位专业的知识分析专家。用中文输出分析结果。",
        f"请分析以下文档：\n\n{source_content[:80000]}",
    )
    await report("analyze", 0.4, "分析完成，准备生成 wiki 页面...")

    # Step 6: LLM 生成
    await report("generate", 0.45, "LLM 生成 wiki 页面...")
    generation_prompt = build_generation_prompt(index, filename, source_content[:80000])
    generation = await call_llm(
        file_store,
        generation_prompt,
        f"分析结果：\n\n{analysis}\n\n---\n\n源文档内容：\n\n{source_content[:80000]}",
    )
    await report("generate", 0.6, "生成完成，处理文件...")

    # Step 7: 解析 FILE 块
    await report("write", 0.7, "写入 wiki 页面...")
    file_blocks, parse_warnings = parse_file_blocks(generation)

    files_written = []
    for block in file_blocks:
        rel_path = block["path"]
        # LLM 生成的路径可能带 wiki/ 前缀，需要去掉
        # 因为 WikiStore.write_page 的路径是相对于 wiki_dir (data/wiki) 的
        wiki_rel = rel_path
        if wiki_rel.startswith("wiki/"):
            wiki_rel = wiki_rel[5:]  # 去掉 wiki/ 前缀

        content_text = block["content"]
        result = parse_frontmatter(content_text)

        if result["frontmatter"]:
            wiki_store.write_page(
                wiki_rel,
                result["frontmatter"],
                result["body"],
                merge=True,
            )
        else:
            # 没有 frontmatter，直接写入
            full_path = Path(settings.DATA_DIR) / "wiki" / wiki_rel
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content_text, encoding="utf-8")

        files_written.append(f"wiki/{wiki_rel}")

    # Step 8: Safety-net 图片注入
    if images:
        await report("images", 0.8, "注入图片到源摘要页...")
        _inject_images_into_source_summary(source_slug, images, wiki_store)

    # Step 9: 解析 REVIEW 块
    await report("reviews", 0.85, "处理审阅项...")
    review_items = parse_review_blocks(generation, source_path=f"wiki/sources/{source_slug}.md")
    if review_items:
        file_store.add_reviews(review_items)

    # Step 10: 保存缓存
    await report("cache", 0.95, "保存缓存...")
    file_store.save_ingest_cache(filename, source_content, files_written)

    await report("done", 1.0, f"摄入完成: {len(files_written)} 个页面, {len(review_items)} 个审阅项")

    return {
        "files_written": files_written,
        "reviews": review_items,
        "warnings": parse_warnings,
        "cached": False,
    }


def _inject_image_descriptions(source_content: str, images: list[dict]) -> str:
    """将图片描述注入到源内容中。"""
    for img in images:
        if not img.get("caption"):
            continue
        old_pattern = f"![]({img['rel_path']})"
        new_text = f"![{img['caption']}]({img['rel_path']})"
        source_content = source_content.replace(old_pattern, new_text)

    if images:
        source_content += "\n\n## 引用的本地图片\n\n"
        for img in images:
            caption = img.get("caption", "无描述")
            source_content += f"- ![{caption}]({img['rel_path']}) — {caption}\n"

    return source_content


MARKER_START = "<!-- daydayknow:embedded-images -->"
MARKER_END = "<!-- /daydayknow:embedded-images -->"


def _inject_images_into_source_summary(
    source_slug: str,
    images: list[dict],
    wiki_store: WikiStore,
):
    """Safety-net: 在源摘要页末尾注入 Embedded Images 区块。

    用标记包围，重复摄入时幂等（先剥离旧注入再写入新注入）。
    """
    # WikiStore 路径相对于 wiki_dir，不需要 wiki/ 前缀
    rel_path = f"sources/{source_slug}.md"
    page = wiki_store.read_page(rel_path)
    if not page:
        return

    body = page["body"]

    # 剥离旧的注入区块
    start_idx = body.find(MARKER_START)
    end_idx = body.find(MARKER_END)
    if start_idx >= 0 and end_idx >= 0:
        body = body[:start_idx] + body[end_idx + len(MARKER_END):]
        body = body.rstrip()

    # 构建新的图片区块
    lines = [MARKER_START, "", "## 嵌入图片", ""]
    current_page = None
    for img in images:
        pg = img.get("page", 0)
        if pg != current_page:
            current_page = pg
            if pg > 0:
                lines.append(f"### 第 {pg} 页")
            else:
                lines.append("### 文档")
        caption = img.get("caption", "")
        alt = caption if caption else img["filename"]
        lines.append(f"![{alt}]({img['rel_path']})")
        lines.append("")

    lines.append(MARKER_END)
    new_section = "\n".join(lines)

    body = body + "\n\n" + new_section

    wiki_store.write_page(rel_path, page["frontmatter"] or {}, body, merge=False)

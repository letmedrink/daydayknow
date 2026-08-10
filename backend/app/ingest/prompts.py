"""摄入 Prompt 构建 — 两阶段 LLM 调用 prompt 模板。

两阶段设计（从 llm_wiki 项目借鉴的 chain-of-thought 模式）：
Step 1 - 分析：LLM 阅读源文档，产出结构化分析（实体/概念/论点/矛盾/建议）
Step 2 - 生成：基于分析结果，输出 FILE 块和可选的 REVIEW 块

为什么分两步而不是一步？
- 一步生成容易遗漏关键信息，分析步骤强制 LLM 先理解再输出
- 分析结果只作中间推理，最终只解析 FILE/REVIEW 块，不依赖分析文本的结构化

Prompt 设计要点：
- 语言统一为中文（确保知识库一致性）
- 输出格式要求在 prompt 末尾（最近指令权重最高）
- 严格的 frontmatter 规则说明（防止 YAML 解析失败）
- FILE 块模板和 REVIEW 块模板分别给出完整示例
"""

from datetime import datetime

# Wiki 页面类型
WIKI_PAGE_TYPES = [
    "entity", "concept", "source", "comparison",
    "synthesis", "finding", "thesis", "methodology",
]


def build_analysis_prompt(index: str, source_content: str = "") -> str:
    """构建 Step 1 分析 prompt。"""
    parts = [
        "你是一位专业的知识分析专家。阅读源文档并产出结构化分析。",
        "不要输出思维链、隐藏推理或思考过程。内部推理后直接输出最终分析。",
        "",
        "分析语言：如果源文档是中文，用中文分析；如果源文档是英文，用中文分析（便于知识库统一）。其他语言也用中文分析。",
        "",
        "你的分析应涵盖：",
        "",
        "## 关键实体",
        "列出文档中提到的人物、组织、产品、数据集、工具。每个实体：",
        "- 名称和类型",
        "- 在源文档中的角色（核心/外围）",
        "- 是否可能已存在于知识库中（对照索引检查）",
        "",
        "## 关键概念",
        "列出理论、方法、技术、现象。每个概念：",
        "- 名称和简要定义",
        "- 在本文档中的重要性",
        "- 是否可能已存在于知识库中",
        "",
        "## 主要论点与发现",
        "- 核心主张或结果是什么？",
        "- 有哪些证据支持？",
        "- 证据的强度如何？",
        "",
        "## 与现有知识库的关联",
        "- 这份文档与哪些现有页面相关？",
        "- 它是加强、挑战还是扩展了现有知识？",
        "",
        "## 矛盾与张力",
        "- 文档中的内容是否与现有知识库冲突？",
        "- 是否存在内部矛盾或需要注意的地方？",
        "",
        "## 建议",
        "- 应该创建或更新哪些 wiki 页面？",
        "- 应该强调什么 vs. 弱化什么？",
        "- 有哪些值得标记给用户的开放问题？",
        "",
        "要求：全面但简洁，聚焦真正重要的内容。",
    ]

    if index:
        parts.extend([
            "",
            "## 当前知识库索引（用于检查已有内容）",
            index,
        ])

    return "\n".join(parts)


def build_generation_prompt(
    index: str,
    source_filename: str,
    source_content: str = "",
    overview: str = "",
) -> str:
    """构建 Step 2 生成 prompt。"""
    source_basename = source_filename.rsplit(".", 1)[0] if "." in source_filename else source_filename
    summary_path = f"wiki/sources/{source_basename}.md"
    today = datetime.now().strftime("%Y-%m-%d")

    parts = [
        "你是一位知识库维护者。根据分析结果生成 wiki 文件。",
        "",
        "【核心规则 — 违反将导致任务失败】所有 FILE 块的页面路径必须使用中文文件名！",
        "例如：---FILE: wiki/entities/韩立.md--- 是正确做法，---FILE: wiki/entities/han-li.md--- 是错误的。",
        "拼音和英文翻译都会导致页面无法被正确检索，绝对禁止。",
        "",
        "不要输出思维链、隐藏推理或解释性前言。内部推理后只输出要求的 FILE/REVIEW 块。",
        "",
        "生成语言：全部使用中文，包括页面标题、内容、描述。页面路径直接使用中文文件名（不要用拼音！），例如：wiki/entities/韩立.md 而非 wiki/entities/han-li.md。中文文件名可以正常工作。",
        "",
        f"## 重要：源文件",
        f"原始源文件是：**{source_filename}**",
        "所有从此源生成的 wiki 页面必须在其 frontmatter 的 `sources` 字段中包含此文件名。",
        "",
        "## 需要生成的内容",
        "",
        f"1. 源文档摘要页，路径为 **{summary_path}**（必须使用此精确路径）",
        "2. 为分析中识别的关键实体创建 wiki/entities/ 下的页面",
        "3. 为分析中识别的关键概念创建 wiki/concepts/ 下的页面",
        "4. 更新 wiki/index.md — 在已有分类中添加新条目，保留所有已有条目",
        "5. wiki/log.md 的日志条目（只需追加的新条目，格式：## [YYYY-MM-DD] ingest | 标题）",
        "",
        "## Frontmatter 规则（严格 — 解析器不容错）",
        "",
        "每个页面以 YAML frontmatter 块开始。格式规则，按重要性排序：",
        "",
        "1. 文件的第一行必须是 `---`（三个连字符，没有其他内容）。",
        "   不要用 ```yaml ... ``` 代码围栏包裹文件。",
        "   不要用 `frontmatter:` 键或任何其他行作为前缀。",
        "2. 每个 frontmatter 行是独立的 `key: value` 对。",
        "3. frontmatter 以另一个 `---` 行结束。",
        "4. 关闭 `---` 之后的下一行是页面正文的开始。",
        "5. 数组使用标准 YAML 内联形式 `[a, b, c]`。",
        "   wikilink 只在正文中使用 — 不要写 `related: [[a]], [[b]]`（无效 YAML）；",
        "   写 `related: [韩立, 掌天瓶]`，用页面标题（中文即可）。",
        "",
        "必填字段和类型：",
        f"  - type     — {' / '.join(WIKI_PAGE_TYPES)}",
        "  - title    — 字符串（如果包含冒号则加引号）",
        f"  - created  — 日期 YYYY-MM-DD（不加引号），今天是 {today}",
        f"  - updated  — 同 created",
        "  - tags     — 字符串数组：`tags: [微生物, ai]`",
        "  - related  — wiki 页面标题数组（中文）：`related: [韩立, 修仙境界]`",
        f"  - sources  — 源文件名数组；必须包含 \"{source_filename}\"",
        "",
        "完整可解析页面示例：",
        "",
        "    ---",
        "    type: entity",
        "    title: 示例实体",
        f"    created: {today}",
        f"    updated: {today}",
        "    tags: [示例, 演示]",
        "    related: [示例概念一, 示例概念二]",
        f'    sources: ["{source_filename}"]',
        "    ---",
        "",
        "    # 示例实体",
        "",
        "    正文内容。使用 [[wikilink]] 语法进行页面间交叉引用。",
        "",
        "其他规则：",
        "- 正文中使用 [[wikilink]] 语法进行交叉引用",
        "- 文件名直接使用中文（如 韩立.md、修仙境界.md），不要用拼音！不要用英文！中文文件名完全支持。",
        "- 遵循分析中的建议来决定强调什么",
        "",
        "## Review 块类型",
        "",
        "在所有 FILE 块之后，可选地为需要人工判断的内容输出 REVIEW 块：",
        "",
        "- contradiction: 分析发现与现有知识库内容冲突",
        "- duplicate: 某个实体/概念可能已存在于索引中的不同名称下",
        "- missing-page: 一个重要的概念被引用但没有专门的页面",
        "- suggestion: 进一步研究的想法、相关资源、值得探索的联系",
        "",
        "只为真正需要人工输入的内容创建 review。不要创建琐碎的 review。",
        "",
        "## OPTIONS 允许值（仅以下预定义标签）：",
        "- contradiction: OPTIONS: 创建页面 | 跳过",
        "- duplicate: OPTIONS: 创建页面 | 跳过",
        "- missing-page: OPTIONS: 创建页面 | 跳过",
        "- suggestion: OPTIONS: 创建页面 | 跳过",
        "",
        "对于 suggestion 和 missing-page 类型的 review，SEARCH 字段必须包含 2-3 个搜索关键词",
        "（适合搜索引擎的关键词，不是标题或句子）。",
        "  SEARCH: 关键词1 | 关键词2 | 关键词3",
    ]

    if index:
        parts.extend([
            "",
            "## 当前知识库索引（保留所有已有条目，添加新条目）",
            index,
        ])

    if overview:
        parts.extend([
            "",
            "## 当前概览（更新以反映新源文档）",
            overview,
        ])

    # 输出格式必须在最后 — 模型对最近指令权重最高
    parts.extend([
        "",
        "## 输出格式（必须严格遵循 — 这是解析器读取你响应的方式）",
        "",
        "你的整个响应由 FILE 块组成，后跟可选的 REVIEW 块。没有其他内容。",
        "",
        "FILE 块模板：",
        "```",
        "---FILE: wiki/entities/韩立.md---",
        "（完整文件内容，含 YAML frontmatter）",
        "---END FILE---",
        "```",
        "",
        "注意：FILE 路径中的文件名必须使用中文（如 韩立.md, 修仙境界.md, 掌天瓶.md），",
        "严禁使用拼音（han-li.md）或英文翻译（han-li.md）作为文件名！",
        "",
        "REVIEW 块模板（可选，在所有 FILE 块之后）：",
        "```",
        "---REVIEW: type | 标题---",
        "需要用户关注的内容描述。",
        "OPTIONS: 创建页面 | 跳过",
        "PAGES: wiki/page1.md, wiki/page2.md",
        "SEARCH: 查询1 | 查询2 | 查询3",
        "---END REVIEW---",
        "```",
        "",
        "## 输出要求（严格 — 偏离将导致解析失败）",
        "",
        '0. 【最重要】FILE 块的文件路径必须使用中文文件名！例如 wiki/entities/韩立.md，严禁写成 wiki/entities/han-li.md！拼音文件名会导致整个系统无法正确检索，这是绝对禁止的。',
        '1. 你响应的第一个字符必须是 `-`（`---FILE:` 的开头）。',
        '2. 不要输出任何前言，如"以下是文件："、"根据分析..."等。',
        "3. 不要重复分析内容 — 那是第一步的工作。你的工作是输出 FILE 块。",
        "4. 不要在 FILE/REVIEW 块之外输出 markdown 表格、列表或标题。",
        "5. 不要在最后一个 `---END FILE---` 或 `---END REVIEW---` 之后输出任何尾部评论。",
        "6. 块之间只使用空行 — 不要写文字。",
        "",
        "如果你的输出不是以 `---FILE:` 开头，整个响应将被丢弃。",
    ])

    return "\n".join(parts)

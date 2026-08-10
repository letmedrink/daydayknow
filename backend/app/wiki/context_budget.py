"""上下文预算分配器 — 控制聊天时 wiki 页面注入的字符预算。

预算是动态的：根据模型的最大上下文窗口自动计算各部分限额。

预算分配策略：
  ┌─────────────────────────────────────────────────┐
  │              maxCtx (100%)                       │
  ├──────┬──────────────┬─────────────────┬──────────┤
  │ idx  │   pages      │  history + sys  │  resp    │
  │  5%  │    50%       │    ~30%         │   15%    │
  └──────┴──────────────┴─────────────────┴──────────┘

索引摘要 (5%)  : wiki 页面列表索引，帮助 LLM 了解知识库全貌
页面内容 (50%) : 直接匹配页 + 1-hop 邻居，是上下文的主要构成
历史+系统 (30%): 对话历史 + system prompt + 用户画像
回复预留 (15%) : 为 LLM 生成回复保留的空间

单页最大字符数 = min(page_budget, max(5000, page_budget × 30%))
默认最大上下文 = 200K 字符
"""

from dataclasses import dataclass


@dataclass
class ContextBudget:
    max_ctx: int           # 模型最大上下文窗口（字符数）
    response_reserve: int  # 为回复预留的空间
    index_budget: int      # wiki 索引摘要预算（~5%）
    page_budget: int       # wiki 页面内容总预算（~50%）
    max_page_size: int     # 单页最大字符数


DEFAULT_MAX_CTX = 204_800
RESPONSE_RESERVE_FRAC = 0.15
INDEX_BUDGET_FRAC = 0.05
PAGE_BUDGET_FRAC = 0.5
PER_PAGE_FRAC = 0.3
PER_PAGE_FLOOR = 5_000


def compute_context_budget(max_context_size: int = 0) -> ContextBudget:
    """根据 LLM 最大上下文窗口计算各部分字符预算。

    Args:
        max_context_size: 模型上下文窗口大小（字符数）。0 或负数使用默认值。
    """
    max_ctx = max_context_size if max_context_size > 0 else DEFAULT_MAX_CTX

    response_reserve = int(max_ctx * RESPONSE_RESERVE_FRAC)
    index_budget = int(max_ctx * INDEX_BUDGET_FRAC)
    page_budget = int(max_ctx * PAGE_BUDGET_FRAC)

    max_page_size = min(
        page_budget,
        max(PER_PAGE_FLOOR, int(page_budget * PER_PAGE_FRAC)),
    )

    return ContextBudget(
        max_ctx=max_ctx,
        response_reserve=response_reserve,
        index_budget=index_budget,
        page_budget=page_budget,
        max_page_size=max_page_size,
    )

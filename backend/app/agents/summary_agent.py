from .base import BaseAgent, AgentResult
from .context import AgentContext
from .registry import AgentRegistry
from ..services.llm.router import ModelRouter

LEVEL_PROMPTS = {
    "detailed": "详细摘要：保留关键问答对、主要概念和推理过程。",
    "medium": "中等摘要：只保留核心概念和结论，省略推理细节。",
    "brief": "简短摘要：只保留讨论主题和关键概念名称。",
}


@AgentRegistry.register("summary")
class SummaryAgent(BaseAgent):
    name = "summary"
    description = "分层压缩长对话历史"

    def __init__(self, keep_recent: int = 10):
        super().__init__()
        self.keep_recent = keep_recent

    async def execute(self, context: AgentContext) -> AgentResult:
        messages = context.messages
        if len(messages) <= self.keep_recent:
            return AgentResult(
                success=True, data={"summaries": [], "compressed": False}
            )

        # 分离需要压缩的消息和保留的消息
        to_compress = messages[: -self.keep_recent]
        # 分轮次：每轮 = user + assistant
        rounds = self._group_rounds(to_compress)

        if not rounds:
            return AgentResult(
                success=True, data={"summaries": [], "compressed": False}
            )

        summaries = []
        for round_group in self._assign_levels(rounds):
            level = round_group["level"]
            round_range = round_group["rounds"]
            text = "\n".join(
                f"{m.role}: {m.content}" for m in round_group["messages"]
            )

            system_prompt = (
                f"你是对话摘要专家。请生成{LEVEL_PROMPTS[level]}\n\n"
                f"输出纯文本摘要，不要包含格式标记。"
            )
            messages_for_llm = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请压缩以下对话：\n\n{text}"},
            ]

            provider = ModelRouter.get_provider()
            try:
                result = await provider.chat(messages_for_llm)
                summaries.append({
                    "start_round": round_range[0],
                    "end_round": round_range[1],
                    "level": level,
                    "text": result,
                })
            except Exception as e:
                self.log.error(f"Summary failed for rounds {round_range}", e)

        return AgentResult(
            success=True, data={"summaries": summaries, "compressed": True}
        )

    @staticmethod
    def _group_rounds(messages: list) -> list[list]:
        """将消息分组为轮次 (user+assistant pairs)。"""
        rounds = []
        current_round = []
        for msg in messages:
            if msg.role == "user":
                if current_round:
                    rounds.append(current_round)
                current_round = [msg]
            elif msg.role == "assistant" and current_round:
                current_round.append(msg)
        if current_round:
            rounds.append(current_round)
        return rounds

    @staticmethod
    def _assign_levels(rounds: list[list]) -> list[dict]:
        """根据轮次位置分配压缩级别。"""
        total = len(rounds)
        groups = []

        if total <= 30:
            # 1~N 轮：全部 detailed
            groups.append({
                "level": "detailed",
                "rounds": (1, total),
                "messages": [m for r in rounds for m in r],
            })
        elif total <= 60:
            # 1~30: detailed, 31~N: medium
            groups.append({
                "level": "detailed",
                "rounds": (1, 30),
                "messages": [m for r in rounds[:30] for m in r],
            })
            groups.append({
                "level": "medium",
                "rounds": (31, total),
                "messages": [m for r in rounds[30:] for m in r],
            })
        else:
            # 1~30: detailed, 31~60: medium, 61+: brief
            groups.append({
                "level": "detailed",
                "rounds": (1, 30),
                "messages": [m for r in rounds[:30] for m in r],
            })
            groups.append({
                "level": "medium",
                "rounds": (31, 60),
                "messages": [m for r in rounds[30:60] for m in r],
            })
            groups.append({
                "level": "brief",
                "rounds": (61, total),
                "messages": [m for r in rounds[60:] for m in r],
            })

        return groups

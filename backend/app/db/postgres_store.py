import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from .models import Base, KgNode, KgEdge, Conversation, Message, UserProfile, KgNodeVersion, ConversationSummary
from ..config import settings


class PostgresGraphStore:
    """PostgreSQL 图谱存储。方法签名与 InMemoryGraphStore 对齐。"""

    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, echo=False)
        self._session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def _session(self) -> AsyncSession:
        return self._session_factory()

    # --- 节点 ---

    async def create_node(
        self,
        user_id: str,
        name: str,
        domain: str | None = None,
        description: str | None = None,
        confidence: float = 0.8,
        source_type: str = "conversation",
        source_ref: str | None = None,
    ) -> dict:
        # 计算 embedding
        from ..services.embedding.router import EmbeddingRouter
        emb_provider = EmbeddingRouter.get_provider()
        search_text = f"{name} {description or ''} {domain or ''}".strip()
        embedding = await emb_provider.embed(search_text)

        async with self._session() as session:
            # 精确名称匹配
            existing = await session.execute(
                select(KgNode).where(KgNode.user_id == user_id, KgNode.name == name)
            )
            row = existing.scalar_one_or_none()
            if row:
                return self._node_to_dict(row)

            # 语义相似度匹配 (pgvector cosine distance < 1 - threshold)
            threshold = settings.EMBEDDING_SIMILARITY_THRESHOLD
            try:
                similar = await session.execute(
                    select(KgNode)
                    .where(
                        KgNode.user_id == user_id,
                        KgNode.embedding.isnot(None),
                        KgNode.embedding.cosine_distance(embedding) < (1.0 - threshold),
                    )
                    .order_by(KgNode.embedding.cosine_distance(embedding))
                    .limit(1)
                )
                match = similar.scalar_one_or_none()
                if match:
                    return self._node_to_dict(match)
            except Exception:
                # pgvector 不可用时降级为精确匹配
                pass

            node = KgNode(
                user_id=user_id,
                name=name,
                domain=domain,
                description=description,
                embedding=embedding,
                confidence=confidence,
                source_type=source_type,
                source_ref=source_ref,
            )
            session.add(node)
            await session.commit()
            await session.refresh(node)
            return self._node_to_dict(node)

    async def get_user_nodes(self, user_id: str, domain: str | None = None) -> List[dict]:
        async with self._session() as session:
            query = select(KgNode).where(KgNode.user_id == user_id)
            if domain:
                query = query.where(KgNode.domain == domain)
            result = await session.execute(query)
            return [self._node_to_dict(n) for n in result.scalars().all()]

    async def get_user_domains(self, user_id: str) -> List[dict]:
        """获取用户的所有领域及节点数量。"""
        async with self._session() as session:
            result = await session.execute(
                select(
                    func.coalesce(KgNode.domain, "未分类").label("name"),
                    func.count(KgNode.id).label("count"),
                )
                .where(KgNode.user_id == user_id)
                .group_by(KgNode.domain)
                .order_by(func.count(KgNode.id).desc())
            )
            return [{"name": row.name, "count": row.count} for row in result.all()]

    # --- 边 ---

    async def create_edge(
        self,
        user_id: str,
        from_node_id: str,
        to_node_id: str,
        relation_type: str,
        strength: float = 1.0,
        description: str | None = None,
        source_ref: str | None = None,
    ) -> dict | None:
        if from_node_id == to_node_id:
            return None
        async with self._session() as session:
            from_uuid = uuid.UUID(from_node_id)
            to_uuid = uuid.UUID(to_node_id)

            existing = await session.execute(
                select(KgEdge).where(
                    KgEdge.user_id == user_id,
                    KgEdge.from_node_id == from_uuid,
                    KgEdge.to_node_id == to_uuid,
                    KgEdge.relation_type == relation_type,
                )
            )
            row = existing.scalar_one_or_none()
            if row:
                return self._edge_to_dict(row)

            edge = KgEdge(
                user_id=user_id,
                from_node_id=from_uuid,
                to_node_id=to_uuid,
                relation_type=relation_type,
                strength=strength,
                description=description,
                source_ref=source_ref,
            )
            session.add(edge)
            await session.commit()
            await session.refresh(edge)
            return self._edge_to_dict(edge)

    async def get_user_edges(self, user_id: str) -> List[dict]:
        async with self._session() as session:
            result = await session.execute(
                select(KgEdge).where(KgEdge.user_id == user_id)
            )
            return [self._edge_to_dict(e) for e in result.scalars().all()]

    async def get_node_with_neighbors(self, node_id: str) -> dict | None:
        """获取节点及其邻居节点和关联边。"""
        from sqlalchemy import or_

        async with self._session() as session:
            node_uuid = uuid.UUID(node_id)
            result = await session.execute(
                select(KgNode).where(KgNode.id == node_uuid)
            )
            node = result.scalar_one_or_none()
            if not node:
                return None

            # 获取关联边
            edge_result = await session.execute(
                select(KgEdge).where(
                    or_(KgEdge.from_node_id == node_uuid, KgEdge.to_node_id == node_uuid),
                    KgEdge.strength > 0,
                )
            )
            edges = [self._edge_to_dict(e) for e in edge_result.scalars().all()]

            # 获取邻居节点
            neighbor_ids = set()
            for e in edges:
                if e["from_node_id"] != node_id:
                    neighbor_ids.add(e["from_node_id"])
                if e["to_node_id"] != node_id:
                    neighbor_ids.add(e["to_node_id"])

            neighbors = []
            if neighbor_ids:
                from sqlalchemy import any_
                nid_uuids = [uuid.UUID(nid) for nid in neighbor_ids]
                neighbor_result = await session.execute(
                    select(KgNode).where(KgNode.id.in_(nid_uuids))
                )
                neighbors = [self._node_to_dict(n) for n in neighbor_result.scalars().all()]

            return {
                "node": self._node_to_dict(node),
                "neighbors": neighbors,
                "edges": edges,
            }

    # --- 批量提取 ---

    async def store_extraction(
        self, user_id: str, extraction: dict, source_ref: str | None = None
    ) -> dict:
        created_nodes = []
        name_to_id = {}
        for node_data in extraction.get("nodes", []):
            node = await self.create_node(
                user_id=user_id,
                name=node_data["name"],
                domain=node_data.get("domain"),
                description=node_data.get("description"),
                confidence=node_data.get("confidence", 0.8),
                source_ref=source_ref,
            )
            created_nodes.append(node)
            name_to_id[node_data["name"]] = node["id"]

        created_edges = []
        for edge_data in extraction.get("edges", []):
            from_id = name_to_id.get(edge_data["from"])
            to_id = name_to_id.get(edge_data["to"])
            if from_id and to_id:
                edge = await self.create_edge(
                    user_id=user_id,
                    from_node_id=from_id,
                    to_node_id=to_id,
                    relation_type=edge_data["relation_type"],
                    strength=edge_data.get("strength", 0.9),
                    description=edge_data.get("description"),
                    source_ref=source_ref,
                )
                if edge:
                    created_edges.append(edge)

        return {"nodes": created_nodes, "edges": created_edges}

    # --- 对话 ---

    async def create_conversation(
        self, user_id: str, title: str | None = None
    ) -> dict:
        async with self._session() as session:
            conv = Conversation(user_id=user_id, title=title)
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
            return self._conv_to_dict(conv)

    async def get_conversation(self, conversation_id: str) -> dict | None:
        async with self._session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
            )
            conv = result.scalar_one_or_none()
            return self._conv_to_dict(conv) if conv else None

    async def list_conversations(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[dict]:
        async with self._session() as session:
            result = await session.execute(
                select(Conversation)
                .where(Conversation.user_id == user_id, Conversation.status == "active")
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return [self._conv_to_dict(c) for c in result.scalars().all()]

    async def search_conversations(
        self, user_id: str, query: str, limit: int = 20
    ) -> List[dict]:
        """按标题搜索对话。"""
        async with self._session() as session:
            result = await session.execute(
                select(Conversation)
                .where(
                    Conversation.user_id == user_id,
                    Conversation.title.ilike(f"%{query}%"),
                )
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
            )
            return [self._conv_to_dict(c) for c in result.scalars().all()]

    async def add_message(
        self, conversation_id: str, role: str, content: str
    ) -> dict:
        async with self._session() as session:
            conv_uuid = uuid.UUID(conversation_id)

            # 获取当前最大 sequence_number
            seq_result = await session.execute(
                select(func.coalesce(func.max(Message.sequence_number), 0))
                .where(Message.conversation_id == conv_uuid)
            )
            next_seq = seq_result.scalar() + 1

            msg = Message(
                conversation_id=conv_uuid,
                role=role,
                content=content,
                sequence_number=next_seq,
            )
            session.add(msg)

            # 更新对话计数器
            await session.execute(
                update(Conversation)
                .where(Conversation.id == conv_uuid)
                .values(
                    message_count=Conversation.message_count + 1,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()
            await session.refresh(msg)
            return self._msg_to_dict(msg)

    async def get_messages(
        self, conversation_id: str, limit: int | None = None, offset: int = 0
    ) -> List[dict]:
        async with self._session() as session:
            query = (
                select(Message)
                .where(Message.conversation_id == uuid.UUID(conversation_id))
                .order_by(Message.sequence_number)
                .offset(offset)
            )
            if limit is not None:
                query = query.limit(limit)
            result = await session.execute(query)
            return [self._msg_to_dict(m) for m in result.scalars().all()]

    async def search_messages(
        self, conversation_id: str, query: str, limit: int = 20
    ) -> List[dict]:
        """搜索对话消息内容。"""
        async with self._session() as session:
            result = await session.execute(
                select(Message)
                .where(
                    Message.conversation_id == uuid.UUID(conversation_id),
                    Message.content.ilike(f"%{query}%"),
                )
                .order_by(Message.sequence_number)
                .limit(limit)
            )
            return [self._msg_to_dict(m) for m in result.scalars().all()]

    async def delete_conversation(self, conversation_id: str) -> bool:
        async with self._session() as session:
            result = await session.execute(
                delete(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
            )
            await session.commit()
            return result.rowcount > 0

    async def rename_conversation(self, conversation_id: str, title: str) -> dict | None:
        async with self._session() as session:
            result = await session.execute(
                update(Conversation)
                .where(Conversation.id == uuid.UUID(conversation_id))
                .values(title=title, updated_at=datetime.now(timezone.utc))
                .returning(Conversation)
            )
            await session.commit()
            row = result.scalar_one_or_none()
            return self._conv_to_dict(row) if row else None

    async def delete_node(self, node_id: str) -> bool:
        """删除节点及其关联边。"""
        async with self._session() as session:
            node_uuid = uuid.UUID(node_id)
            # 删除关联边
            await session.execute(
                delete(KgEdge).where(
                    (KgEdge.from_node_id == node_uuid) | (KgEdge.to_node_id == node_uuid)
                )
            )
            # 删除节点
            result = await session.execute(
                delete(KgNode).where(KgNode.id == node_uuid)
            )
            await session.commit()
            return result.rowcount > 0

    async def delete_nodes_bulk(self, user_id: str, node_ids: List[str]) -> int:
        """批量删除节点及其关联边。返回删除数量。"""
        async with self._session() as session:
            node_uuids = [uuid.UUID(nid) for nid in node_ids]
            # 删除关联边
            from sqlalchemy import or_
            await session.execute(
                delete(KgEdge).where(
                    or_(KgEdge.from_node_id.in_(node_uuids), KgEdge.to_node_id.in_(node_uuids))
                )
            )
            # 删除节点
            result = await session.execute(
                delete(KgNode).where(
                    KgNode.user_id == user_id,
                    KgNode.id.in_(node_uuids),
                )
            )
            await session.commit()
            return result.rowcount

    async def delete_edge(self, edge_id: str) -> bool:
        """删除单条边。"""
        async with self._session() as session:
            result = await session.execute(
                delete(KgEdge).where(KgEdge.id == uuid.UUID(edge_id))
            )
            await session.commit()
            return result.rowcount > 0

    async def update_edge(self, edge_id: str, updates: dict) -> dict | None:
        """更新边属性。"""
        async with self._session() as session:
            values = {}
            for key in ("relation_type", "strength", "description"):
                if key in updates and updates[key] is not None:
                    values[key] = updates[key]
            if not values:
                # 没有更新
                result = await session.execute(
                    select(KgEdge).where(KgEdge.id == uuid.UUID(edge_id))
                )
                row = result.scalar_one_or_none()
                return self._edge_to_dict(row) if row else None

            result = await session.execute(
                update(KgEdge)
                .where(KgEdge.id == uuid.UUID(edge_id))
                .values(**values)
                .returning(KgEdge)
            )
            await session.commit()
            row = result.scalar_one_or_none()
            return self._edge_to_dict(row) if row else None

    async def delete_conversations_bulk(self, user_id: str, conversation_ids: List[str]) -> int:
        """批量删除对话。返回删除数量。"""
        async with self._session() as session:
            conv_uuids = [uuid.UUID(cid) for cid in conversation_ids]
            result = await session.execute(
                delete(Conversation).where(
                    Conversation.user_id == user_id,
                    Conversation.id.in_(conv_uuids),
                )
            )
            await session.commit()
            return result.rowcount

    # --- 用户画像 ---

    async def save_profile(self, user_id: str, profile_data: dict) -> dict:
        async with self._session() as session:
            existing = await session.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            row = existing.scalar_one_or_none()
            now = datetime.now(timezone.utc)

            if row:
                merged = self._merge_profile(row.profile_data, profile_data)
                row.profile_data = merged
                row.version += 1
                row.updated_at = now
                await session.commit()
                await session.refresh(row)
            else:
                row = UserProfile(user_id=user_id, profile_data=profile_data)
                session.add(row)
                await session.commit()
                await session.refresh(row)

            return {
                "user_id": row.user_id,
                "data": row.profile_data,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
            }

    async def get_profile(self, user_id: str) -> dict | None:
        async with self._session() as session:
            result = await session.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            return {
                "user_id": row.user_id,
                "data": row.profile_data,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
            }

    @staticmethod
    def _merge_profile(existing: dict, new: dict) -> dict:
        merged = dict(existing)
        for key, value in new.items():
            if value is None:
                continue
            if isinstance(value, list):
                old_list = merged.get(key, [])
                try:
                    merged[key] = list(dict.fromkeys(old_list + value))
                except TypeError:
                    merged[key] = old_list + value
            elif isinstance(value, dict):
                old_dict = merged.get(key, {})
                merged[key] = {**old_dict, **value}
            else:
                merged[key] = value
        return merged

    # --- 知识版本化 ---

    async def supersede_node(
        self,
        node_id: str,
        new_data: dict,
        reason: str = "conflict resolution",
        source_ref: str | None = None,
    ) -> dict | None:
        async with self._session() as session:
            node_uuid = uuid.UUID(node_id)
            result = await session.execute(
                select(KgNode).where(KgNode.id == node_uuid)
            )
            node = result.scalar_one_or_none()
            if not node:
                return None

            # 保存旧版本
            version = KgNodeVersion(
                node_id=node_uuid,
                version=node.current_version,
                name=node.name,
                domain=node.domain,
                description=node.description,
                confidence=node.confidence,
                source_ref=source_ref,
                superseded_reason=reason,
            )
            session.add(version)

            # 更新节点
            node.name = new_data.get("name", node.name)
            node.domain = new_data.get("domain", node.domain)
            node.description = new_data.get("description", node.description)
            node.confidence = new_data.get("confidence", node.confidence)
            node.current_version += 1
            node.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(node)
            return self._node_to_dict(node)

    async def soft_delete_edges(self, user_id: str, node_ids: list[str]) -> int:
        async with self._session() as session:
            uuids = [uuid.UUID(nid) for nid in node_ids]
            from sqlalchemy import or_
            result = await session.execute(
                update(KgEdge)
                .where(
                    KgEdge.user_id == user_id,
                    KgEdge.strength > 0,
                    or_(KgEdge.from_node_id.in_(uuids), KgEdge.to_node_id.in_(uuids)),
                )
                .values(strength=0)
            )
            await session.commit()
            return result.rowcount

    async def get_node_versions(self, node_id: str) -> List[dict]:
        async with self._session() as session:
            result = await session.execute(
                select(KgNodeVersion)
                .where(KgNodeVersion.node_id == uuid.UUID(node_id))
                .order_by(KgNodeVersion.version)
            )
            return [
                {
                    "node_id": str(v.node_id),
                    "version": v.version,
                    "name": v.name,
                    "domain": v.domain,
                    "description": v.description,
                    "confidence": v.confidence,
                    "source_ref": v.source_ref,
                    "superseded_reason": v.superseded_reason,
                    "created_at": v.created_at.isoformat(),
                }
                for v in result.scalars().all()
            ]

    # --- 对话摘要 ---

    async def save_summary(
        self,
        conversation_id: str,
        start_round: int,
        end_round: int,
        summary_text: str,
    ) -> dict:
        async with self._session() as session:
            record = ConversationSummary(
                conversation_id=uuid.UUID(conversation_id),
                start_round=start_round,
                end_round=end_round,
                summary_text=summary_text,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return {
                "id": str(record.id),
                "conversation_id": str(record.conversation_id),
                "start_round": record.start_round,
                "end_round": record.end_round,
                "summary_text": record.summary_text,
                "created_at": record.created_at.isoformat(),
            }

    async def get_summaries(self, conversation_id: str) -> List[dict]:
        async with self._session() as session:
            result = await session.execute(
                select(ConversationSummary)
                .where(ConversationSummary.conversation_id == uuid.UUID(conversation_id))
                .order_by(ConversationSummary.start_round)
            )
            return [
                {
                    "id": str(s.id),
                    "conversation_id": str(s.conversation_id),
                    "start_round": s.start_round,
                    "end_round": s.end_round,
                    "summary_text": s.summary_text,
                    "created_at": s.created_at.isoformat(),
                }
                for s in result.scalars().all()
            ]

    # --- 搜索 ---

    async def search_nodes(
        self,
        user_id: str,
        query: str,
        limit: int = 20,
    ) -> List[dict]:
        """搜索节点：优先语义向量搜索，降级为文本模糊匹配。"""
        from ..services.embedding.router import EmbeddingRouter
        from sqlalchemy import or_

        async with self._session() as session:
            # 尝试语义搜索
            try:
                emb_provider = EmbeddingRouter.get_provider()
                query_emb = await emb_provider.embed(query)
                threshold = settings.EMBEDDING_SIMILARITY_THRESHOLD
                result = await session.execute(
                    select(KgNode)
                    .where(
                        KgNode.user_id == user_id,
                        KgNode.embedding.isnot(None),
                        KgNode.embedding.cosine_distance(query_emb) < (1.0 - threshold),
                    )
                    .order_by(KgNode.embedding.cosine_distance(query_emb))
                    .limit(limit)
                )
                nodes = result.scalars().all()
                if nodes:
                    return [
                        {**self._node_to_dict(n), "_score": 1.0}
                        for n in nodes
                    ]
            except Exception:
                pass

            # 降级为文本模糊匹配
            pattern = f"%{query}%"
            result = await session.execute(
                select(KgNode)
                .where(
                    KgNode.user_id == user_id,
                    or_(
                        KgNode.name.ilike(pattern),
                        KgNode.description.ilike(pattern),
                        KgNode.domain.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
            return [
                {**self._node_to_dict(n), "_score": 0.5}
                for n in result.scalars().all()
            ]

    # --- 统计 ---

    async def get_statistics(self, user_id: str) -> dict:
        """获取用户知识图谱统计。"""
        from sqlalchemy import func, case

        async with self._session() as session:
            # 节点数
            node_count = await session.execute(
                select(func.count(KgNode.id)).where(KgNode.user_id == user_id)
            )
            total_nodes = node_count.scalar() or 0

            # 边数（有效）
            edge_count = await session.execute(
                select(func.count(KgEdge.id)).where(
                    KgEdge.user_id == user_id, KgEdge.strength > 0
                )
            )
            total_edges = edge_count.scalar() or 0

            # 对话数
            conv_count = await session.execute(
                select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
            )
            total_conversations = conv_count.scalar() or 0

            # 领域分布
            domain_result = await session.execute(
                select(
                    func.coalesce(KgNode.domain, "未分类").label("domain"),
                    func.count(KgNode.id).label("count"),
                )
                .where(KgNode.user_id == user_id)
                .group_by(KgNode.domain)
                .order_by(func.count(KgNode.id).desc())
            )
            domains = {row.domain: row.count for row in domain_result.all()}

            # Top 连接节点
            top_result = await session.execute(
                select(
                    KgNode.id,
                    KgNode.name,
                    func.count(KgEdge.id).label("connections"),
                )
                .join(KgEdge, (KgEdge.from_node_id == KgNode.id) | (KgEdge.to_node_id == KgNode.id))
                .where(KgNode.user_id == user_id, KgEdge.strength > 0)
                .group_by(KgNode.id, KgNode.name)
                .order_by(func.count(KgEdge.id).desc())
                .limit(10)
            )
            top_nodes = [
                {"name": row.name, "connections": row.connections}
                for row in top_result.all()
            ]

            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "total_conversations": total_conversations,
                "domains": domains,
                "top_connected_nodes": top_nodes,
            }

    async def export_graph(
        self,
        user_id: str,
        fmt: str = "json",
    ) -> dict:
        """导出用户知识图谱数据。"""
        nodes = await self.get_user_nodes(user_id)
        edges = await self.get_user_edges(user_id)
        clean_nodes = [
            {k: v for k, v in n.items() if k != "user_id"}
            for n in nodes
        ]
        clean_edges = [
            {k: v for k, v in e.items() if k != "user_id"}
            for e in edges
        ]
        return {"nodes": clean_nodes, "edges": clean_edges}

    # --- 转换辅助 ---

    @staticmethod
    def _node_to_dict(n: KgNode) -> dict:
        return {
            "id": str(n.id),
            "user_id": n.user_id,
            "name": n.name,
            "domain": n.domain,
            "description": n.description,
            "confidence": n.confidence,
            "source_type": n.source_type,
            "source_ref": n.source_ref,
            "current_version": n.current_version,
            "created_at": n.created_at.isoformat(),
        }

    @staticmethod
    def _edge_to_dict(e: KgEdge) -> dict:
        return {
            "id": str(e.id),
            "user_id": e.user_id,
            "from_node_id": str(e.from_node_id),
            "to_node_id": str(e.to_node_id),
            "relation_type": e.relation_type,
            "strength": e.strength,
            "description": e.description,
            "source_ref": e.source_ref,
            "created_at": e.created_at.isoformat(),
        }

    @staticmethod
    def _conv_to_dict(c: Conversation) -> dict:
        return {
            "id": str(c.id),
            "user_id": c.user_id,
            "title": c.title,
            "status": c.status,
            "message_count": c.message_count,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }

    @staticmethod
    def _msg_to_dict(m: Message) -> dict:
        return {
            "id": str(m.id),
            "conversation_id": str(m.conversation_id),
            "role": m.role,
            "content": m.content,
            "sequence_number": m.sequence_number,
            "created_at": m.created_at.isoformat(),
        }

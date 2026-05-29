import uuid
from datetime import datetime, timezone
from typing import Dict, List


class InMemoryGraphStore:
    """内存图谱存储，POC 阶段使用。数据结构与 PG schema 对齐。"""

    def __init__(self):
        self.nodes: Dict[str, dict] = {}
        self.edges: Dict[str, dict] = {}
        self.conversations: Dict[str, dict] = {}
        self.messages: Dict[str, List[dict]] = {}
        self.profiles: Dict[str, dict] = {}
        self.node_versions: Dict[str, List[dict]] = {}  # node_id → [version records]
        self.summaries: Dict[str, List[dict]] = {}  # conversation_id → [summaries]

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
        for node in self.nodes.values():
            if node["user_id"] == user_id and node["name"] == name:
                return node
        node_id = str(uuid.uuid4())
        node = {
            "id": node_id,
            "user_id": user_id,
            "name": name,
            "domain": domain,
            "description": description,
            "confidence": confidence,
            "source_type": source_type,
            "source_ref": source_ref,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.nodes[node_id] = node
        return node

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
        for edge in self.edges.values():
            if (
                edge["user_id"] == user_id
                and edge["from_node_id"] == from_node_id
                and edge["to_node_id"] == to_node_id
                and edge["relation_type"] == relation_type
            ):
                return edge
        edge_id = str(uuid.uuid4())
        edge = {
            "id": edge_id,
            "user_id": user_id,
            "from_node_id": from_node_id,
            "to_node_id": to_node_id,
            "relation_type": relation_type,
            "strength": strength,
            "description": description,
            "source_ref": source_ref,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.edges[edge_id] = edge
        return edge

    async def get_user_nodes(self, user_id: str, domain: str | None = None) -> List[dict]:
        nodes = [n for n in self.nodes.values() if n["user_id"] == user_id]
        if domain:
            nodes = [n for n in nodes if n.get("domain") == domain]
        return nodes

    async def get_user_domains(self, user_id: str) -> List[dict]:
        """获取用户的所有领域及节点数量。"""
        counts: Dict[str, int] = {}
        for node in self.nodes.values():
            if node["user_id"] != user_id:
                continue
            d = node.get("domain") or "未分类"
            counts[d] = counts.get(d, 0) + 1
        return [
            {"name": name, "count": count}
            for name, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)
        ]

    async def get_user_edges(self, user_id: str) -> List[dict]:
        return [e for e in self.edges.values() if e["user_id"] == user_id]

    async def get_node_with_neighbors(self, node_id: str) -> dict | None:
        """获取节点及其邻居节点和关联边。"""
        node = self.nodes.get(node_id)
        if not node:
            return None

        neighbors = []
        edges = []
        for edge in self.edges.values():
            if edge.get("strength", 0) <= 0:
                continue
            if edge["from_node_id"] == node_id:
                edges.append(edge)
                neighbor = self.nodes.get(edge["to_node_id"])
                if neighbor:
                    neighbors.append(neighbor)
            elif edge["to_node_id"] == node_id:
                edges.append(edge)
                neighbor = self.nodes.get(edge["from_node_id"])
                if neighbor:
                    neighbors.append(neighbor)

        return {
            "node": node,
            "neighbors": neighbors,
            "edges": edges,
        }

    async def delete_node(self, node_id: str) -> bool:
        """删除节点及其关联边。"""
        if node_id not in self.nodes:
            return False
        del self.nodes[node_id]
        # 删除关联边
        to_remove = [
            eid for eid, e in self.edges.items()
            if e["from_node_id"] == node_id or e["to_node_id"] == node_id
        ]
        for eid in to_remove:
            del self.edges[eid]
        return True

    async def delete_nodes_bulk(self, user_id: str, node_ids: List[str]) -> int:
        """批量删除节点及其关联边。返回删除数量。"""
        count = 0
        for nid in node_ids:
            node = self.nodes.get(nid)
            if node and node["user_id"] == user_id:
                del self.nodes[nid]
                count += 1
        # 删除关联边
        id_set = set(node_ids)
        to_remove = [
            eid for eid, e in self.edges.items()
            if e["from_node_id"] in id_set or e["to_node_id"] in id_set
        ]
        for eid in to_remove:
            del self.edges[eid]
        return count

    async def delete_edge(self, edge_id: str) -> bool:
        """删除单条边。"""
        if edge_id not in self.edges:
            return False
        del self.edges[edge_id]
        return True

    async def update_edge(self, edge_id: str, updates: dict) -> dict | None:
        """更新边属性。"""
        edge = self.edges.get(edge_id)
        if not edge:
            return None
        for key in ("relation_type", "strength", "description"):
            if key in updates and updates[key] is not None:
                edge[key] = updates[key]
        return edge

    async def delete_conversations_bulk(self, user_id: str, conversation_ids: List[str]) -> int:
        """批量删除对话。返回删除数量。"""
        count = 0
        for cid in conversation_ids:
            conv = self.conversations.get(cid)
            if conv and conv["user_id"] == user_id:
                del self.conversations[cid]
                self.messages.pop(cid, None)
                count += 1
        return count

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

    # --- 对话持久化 ---

    async def create_conversation(
        self, user_id: str, title: str | None = None
    ) -> dict:
        conv_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conv = {
            "id": conv_id,
            "user_id": user_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
        }
        self.conversations[conv_id] = conv
        self.messages[conv_id] = []
        return conv

    async def get_conversation(self, conversation_id: str) -> dict | None:
        return self.conversations.get(conversation_id)

    async def list_conversations(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[dict]:
        user_convs = [
            c for c in self.conversations.values() if c["user_id"] == user_id
        ]
        user_convs.sort(key=lambda c: c["updated_at"], reverse=True)
        return user_convs[offset : offset + limit]

    async def search_conversations(
        self, user_id: str, query: str, limit: int = 20
    ) -> List[dict]:
        """按标题搜索对话。"""
        q = query.lower()
        results = []
        for conv in self.conversations.values():
            if conv["user_id"] != user_id:
                continue
            title = (conv.get("title") or "").lower()
            if q in title:
                results.append(conv)
        results.sort(key=lambda c: c["updated_at"], reverse=True)
        return results[:limit]

    async def add_message(
        self, conversation_id: str, role: str, content: str
    ) -> dict:
        conv = self.conversations[conversation_id]
        msg = {
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.messages[conversation_id].append(msg)
        conv["message_count"] += 1
        conv["updated_at"] = msg["created_at"]
        return msg

    async def get_messages(
        self, conversation_id: str, limit: int | None = None, offset: int = 0
    ) -> List[dict]:
        msgs = list(self.messages.get(conversation_id, []))
        if limit is not None:
            return msgs[offset : offset + limit]
        return msgs[offset:]

    async def search_messages(
        self, conversation_id: str, query: str, limit: int = 20
    ) -> List[dict]:
        """搜索对话消息内容。"""
        q = query.lower()
        results = []
        for msg in self.messages.get(conversation_id, []):
            content = (msg.get("content") or "").lower()
            if q in content:
                results.append(msg)
        return results[:limit]

    async def delete_conversation(self, conversation_id: str) -> bool:
        if conversation_id not in self.conversations:
            return False
        del self.conversations[conversation_id]
        self.messages.pop(conversation_id, None)
        return True

    async def rename_conversation(self, conversation_id: str, title: str) -> dict | None:
        conv = self.conversations.get(conversation_id)
        if not conv:
            return None
        conv["title"] = title
        conv["updated_at"] = datetime.now(timezone.utc).isoformat()
        return conv

    # --- 用户画像 ---

    async def save_profile(self, user_id: str, profile_data: dict) -> dict:
        existing = self.profiles.get(user_id)
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            merged = self._merge_profile(existing["data"], profile_data)
            profile = {
                "user_id": user_id,
                "data": merged,
                "created_at": existing["created_at"],
                "updated_at": now,
            }
        else:
            profile = {
                "user_id": user_id,
                "data": profile_data,
                "created_at": now,
                "updated_at": now,
            }
        self.profiles[user_id] = profile
        return profile

    async def get_profile(self, user_id: str) -> dict | None:
        return self.profiles.get(user_id)

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
        """创建节点新版本，旧版本标记为 superseded。"""
        node = self.nodes.get(node_id)
        if not node:
            return None

        # 保存旧版本记录
        version_record = {
            "node_id": node_id,
            "version": node.get("current_version", 1),
            "name": node["name"],
            "domain": node.get("domain"),
            "description": node.get("description"),
            "confidence": node.get("confidence", 0.8),
            "source_ref": source_ref,
            "superseded_reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if node_id not in self.node_versions:
            self.node_versions[node_id] = []
        self.node_versions[node_id].append(version_record)

        # 更新节点
        node.update({
            "name": new_data.get("name", node["name"]),
            "domain": new_data.get("domain", node.get("domain")),
            "description": new_data.get("description", node.get("description")),
            "confidence": new_data.get("confidence", node.get("confidence", 0.8)),
            "current_version": node.get("current_version", 1) + 1,
        })
        return node

    async def soft_delete_edges(self, user_id: str, node_ids: list[str]) -> int:
        """将涉及指定节点的边标记为 strength=0（软删除）。"""
        count = 0
        for edge in self.edges.values():
            if (
                edge["user_id"] == user_id
                and edge.get("strength", 0) > 0
                and (edge["from_node_id"] in node_ids or edge["to_node_id"] in node_ids)
            ):
                edge["strength"] = 0
                count += 1
        return count

    async def get_node_versions(self, node_id: str) -> List[dict]:
        """获取节点历史版本。"""
        return list(self.node_versions.get(node_id, []))

    # --- 对话摘要 ---

    async def save_summary(
        self,
        conversation_id: str,
        start_round: int,
        end_round: int,
        summary_text: str,
    ) -> dict:
        """保存对话压缩摘要。"""
        record = {
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "start_round": start_round,
            "end_round": end_round,
            "summary_text": summary_text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if conversation_id not in self.summaries:
            self.summaries[conversation_id] = []
        self.summaries[conversation_id].append(record)
        return record

    async def get_summaries(self, conversation_id: str) -> List[dict]:
        """获取对话所有摘要，按轮次排序。"""
        records = self.summaries.get(conversation_id, [])
        return sorted(records, key=lambda r: r["start_round"])

    # --- 搜索 ---

    async def search_nodes(
        self,
        user_id: str,
        query: str,
        limit: int = 20,
    ) -> List[dict]:
        """按关键词搜索节点（名称 + 描述模糊匹配）。"""
        q = query.lower()
        results = []
        for node in self.nodes.values():
            if node["user_id"] != user_id:
                continue
            name = (node.get("name") or "").lower()
            desc = (node.get("description") or "").lower()
            domain = (node.get("domain") or "").lower()
            if q in name or q in desc or q in domain:
                # 简单评分：名称匹配优先
                score = 1.0 if q in name else 0.5
                results.append({**node, "_score": score})
        results.sort(key=lambda n: n["_score"], reverse=True)
        return results[:limit]

    # --- 统计 ---

    async def get_statistics(self, user_id: str) -> dict:
        """获取用户知识图谱统计。"""
        user_nodes = [n for n in self.nodes.values() if n["user_id"] == user_id]
        user_edges = [e for e in self.edges.values() if e["user_id"] == user_id and e.get("strength", 0) > 0]

        # 领域分布
        domains: Dict[str, int] = {}
        for node in user_nodes:
            d = node.get("domain") or "未分类"
            domains[d] = domains.get(d, 0) + 1

        # 节点连接数
        connection_count: Dict[str, int] = {}
        for edge in user_edges:
            connection_count[edge["from_node_id"]] = connection_count.get(edge["from_node_id"], 0) + 1
            connection_count[edge["to_node_id"]] = connection_count.get(edge["to_node_id"], 0) + 1

        # Top 连接节点
        node_name = {n["id"]: n["name"] for n in user_nodes}
        top_connected = sorted(connection_count.items(), key=lambda x: x[1], reverse=True)[:10]
        top_nodes = [
            {"name": node_name.get(nid, nid), "connections": count}
            for nid, count in top_connected
        ]

        # 对话数
        user_convs = [c for c in self.conversations.values() if c["user_id"] == user_id]

        return {
            "total_nodes": len(user_nodes),
            "total_edges": len(user_edges),
            "total_conversations": len(user_convs),
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
        # 去掉内部字段
        clean_nodes = [
            {k: v for k, v in n.items() if k != "user_id"}
            for n in nodes
        ]
        clean_edges = [
            {k: v for k, v in e.items() if k != "user_id"}
            for e in edges
        ]
        return {"nodes": clean_nodes, "edges": clean_edges}

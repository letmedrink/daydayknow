import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

class MockSupabase:
    """模拟 Supabase 客户端"""
    
    def __init__(self):
        self.tables = {
            "terms": [],
            "daily_docs": [],
            "star_nodes": [],
            "star_edges": []
        }
        self.initialized_users = set()
    
    def from_(self, table: str):
        """模拟 from 方法"""
        return MockQueryBuilder(self, table)
    
    def init_mock_data(self, user_id: str):
        """初始化模拟数据"""
        if user_id in self.initialized_users:
            return None
        
        self.initialized_users.add(user_id)
        
        # 添加测试术语
        mock_terms = [
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "term": "流动性陷阱",
                "original_context": "日本经济长期陷入流动性陷阱",
                "domain": "宏观经济学",
                "confidence": 0.9,
                "processed_status": "done",
                "captured_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "term": "零利率下限",
                "original_context": "央行面临零利率下限的约束",
                "domain": "宏观经济学",
                "confidence": 0.85,
                "processed_status": "done",
                "captured_at": datetime.now().isoformat()
            }
        ]
        
        # 添加测试日报
        mock_daily_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "doc_date": datetime.now().strftime("%Y-%m-%d"),
            "cards": [
                {
                    "term_id": mock_terms[0]["id"],
                    "term": "流动性陷阱",
                    "context": "日本经济长期陷入流动性陷阱",
                    "simple": "央行撒钱，但大家都不敢花",
                    "deep": "流动性陷阱是指当利率降到极低水平时，人们预期利率只会上升，因此宁愿持有现金也不愿投资或消费，导致货币政策失效的情况。这时央行增加货币供应量也无法刺激经济增长。",
                    "case": "日本1990年代泡沫破裂后，央行将利率降到接近零，但企业和个人仍不愿借贷消费，经济长期低迷，这就是典型的流动性陷阱。",
                    "history": "流动性陷阱概念最早由凯恩斯在1936年《就业、利息和货币通论》中提出。",
                    "related": ["零利率下限", "量化宽松", "货币政策"],
                    "controversy": "部分经济学家认为流动性陷阱只是理论假设，现实中很少真正出现。",
                    "source": "维基百科"
                }
            ],
            "term_count": 1,
            "generated_at": datetime.now().isoformat()
        }
        
        self.tables["terms"].extend(mock_terms)
        self.tables["daily_docs"].append(mock_daily_doc)
        
        return {"mockTerms": mock_terms, "mockDailyDoc": mock_daily_doc}

class MockQueryBuilder:
    """模拟 Supabase 查询构建器"""
    
    def __init__(self, client: MockSupabase, table: str):
        self.client = client
        self.table = table
        self.filters = []
        self.select_fields = "*"
    
    def select(self, fields: str = "*"):
        """模拟 select 方法"""
        self.select_fields = fields
        return self
    
    def insert(self, data: dict):
        """模拟 insert 方法"""
        new_item = {**data, "id": data.get("id", str(uuid.uuid4()))}
        self.client.tables[self.table].append(new_item)
        self._last_result = {"data": new_item, "error": None}
        return self
    
    def execute(self):
        """模拟 execute 方法"""
        if hasattr(self, '_last_result'):
            result = self._last_result
            del self._last_result
            return result
        data = self._execute_filters()
        return {"data": data, "error": None}
    
    def update(self, data: dict):
        """模拟 update 方法"""
        return MockUpdateBuilder(self.client, self.table, data)
    
    def eq(self, field: str, value: Any):
        """模拟 eq 方法"""
        self.filters.append({"field": field, "value": value, "operator": "eq"})
        return self
    
    def gte(self, field: str, value: Any):
        """模拟 gte 方法"""
        self.filters.append({"field": field, "value": value, "operator": "gte"})
        return self
    
    def lte(self, field: str, value: Any):
        """模拟 lte 方法"""
        self.filters.append({"field": field, "value": value, "operator": "lte"})
        return self
    
    def in_(self, field: str, values: List[Any]):
        """模拟 in 方法"""
        self.filters.append({"field": field, "value": values, "operator": "in"})
        return self
    
    def neq(self, field: str, value: Any):
        """模拟 neq 方法"""
        self.filters.append({"field": field, "value": value, "operator": "neq"})
        return self
    
    def or_(self, conditions: str):
        """模拟 or 方法（简化实现）"""
        return self
    
    def order(self, field: str, ascending: bool = True):
        """模拟 order 方法"""
        return self
    
    def limit(self, count: int):
        """模拟 limit 方法"""
        return self
    
    def single(self):
        """模拟 single 方法"""
        data = self._execute_filters()
        if data:
            return {"data": data[0], "error": None}
        return {"data": None, "error": {"message": "Not found"}}
    
    def execute(self):
        """模拟 execute 方法"""
        data = self._execute_filters()
        return {"data": data, "error": None}
    
    def _execute_filters(self):
        """执行过滤器"""
        data = list(self.client.tables[self.table])
        
        for filter_item in self.filters:
            field = filter_item["field"]
            value = filter_item["value"]
            operator = filter_item["operator"]
            
            if operator == "eq":
                data = [item for item in data if item.get(field) == value]
            elif operator == "gte":
                data = [item for item in data if item.get(field) >= value]
            elif operator == "lte":
                data = [item for item in data if item.get(field) <= value]
            elif operator == "in":
                data = [item for item in data if item.get(field) in value]
            elif operator == "neq":
                data = [item for item in data if item.get(field) != value]
        
        return data

class MockUpdateBuilder:
    """模拟 Supabase 更新构建器"""
    
    def __init__(self, client: MockSupabase, table: str, data: dict):
        self.client = client
        self.table = table
        self.data = data
    
    def eq(self, field: str, value: Any):
        """模拟 eq 方法"""
        table_data = self.client.tables[self.table]
        for i, item in enumerate(table_data):
            if item.get(field) == value:
                table_data[i] = {**item, **self.data}
                return {"data": table_data[i], "error": None}
        return {"data": None, "error": {"message": "Not found"}}
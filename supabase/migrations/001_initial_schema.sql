-- 日知录数据库表结构

-- 术语记录表
CREATE TABLE IF NOT EXISTS terms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    term TEXT NOT NULL,
    original_context TEXT,
    domain TEXT DEFAULT 'unknown',
    confidence REAL DEFAULT 0.0,
    processed_status TEXT DEFAULT 'pending' CHECK (processed_status IN ('pending', 'done')),
    captured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 日报文档表
CREATE TABLE IF NOT EXISTS daily_docs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    doc_date DATE NOT NULL,
    cards JSONB DEFAULT '[]',
    term_count INTEGER DEFAULT 0,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, doc_date)
);

-- 星图节点表
CREATE TABLE IF NOT EXISTS star_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    term_id UUID REFERENCES terms(id) ON DELETE CASCADE,
    term_name TEXT NOT NULL,
    domain TEXT,
    x REAL DEFAULT 0,
    y REAL DEFAULT 0,
    confirmed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 星图连线表
CREATE TABLE IF NOT EXISTS star_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    from_node_id UUID REFERENCES star_nodes(id) ON DELETE CASCADE,
    to_node_id UUID REFERENCES star_nodes(id) ON DELETE CASCADE,
    relation_type TEXT DEFAULT 'related',
    description TEXT,
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_terms_user_id ON terms(user_id);
CREATE INDEX IF NOT EXISTS idx_terms_processed_status ON terms(processed_status);
CREATE INDEX IF NOT EXISTS idx_daily_docs_user_id ON daily_docs(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_docs_doc_date ON daily_docs(doc_date);
CREATE INDEX IF NOT EXISTS idx_star_nodes_user_id ON star_nodes(user_id);
CREATE INDEX IF NOT EXISTS idx_star_edges_user_id ON star_edges(user_id);

-- 启用行级安全策略（RLS）
ALTER TABLE terms ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_docs ENABLE ROW LEVEL SECURITY;
ALTER TABLE star_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE star_edges ENABLE ROW LEVEL SECURITY;

-- 创建策略（允许用户访问自己的数据）
CREATE POLICY "Users can view own terms" ON terms FOR SELECT USING (auth.uid()::text = user_id);
CREATE POLICY "Users can insert own terms" ON terms FOR INSERT WITH CHECK (auth.uid()::text = user_id);
CREATE POLICY "Users can update own terms" ON terms FOR UPDATE USING (auth.uid()::text = user_id);

CREATE POLICY "Users can view own daily_docs" ON daily_docs FOR SELECT USING (auth.uid()::text = user_id);
CREATE POLICY "Users can insert own daily_docs" ON daily_docs FOR INSERT WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can view own star_nodes" ON star_nodes FOR SELECT USING (auth.uid()::text = user_id);
CREATE POLICY "Users can insert own star_nodes" ON star_nodes FOR INSERT WITH CHECK (auth.uid()::text = user_id);
CREATE POLICY "Users can update own star_nodes" ON star_nodes FOR UPDATE USING (auth.uid()::text = user_id);

CREATE POLICY "Users can view own star_edges" ON star_edges FOR SELECT USING (auth.uid()::text = user_id);
CREATE POLICY "Users can insert own star_edges" ON star_edges FOR INSERT WITH CHECK (auth.uid()::text = user_id);
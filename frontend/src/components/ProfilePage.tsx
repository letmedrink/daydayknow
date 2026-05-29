import { useState, useEffect } from 'react';
import { fetchProfile } from '../lib/api';
import type { UserProfile } from '../types';

const STYLE_LABELS: Record<string, string> = {
  analogy: '类比型', formula: '公式型', case: '案例型', diagram: '图解型',
};
const COGNITIVE_LABELS: Record<string, string> = {
  'top-down': '自上而下', 'bottom-up': '自下而上', mixed: '混合型',
};
const DEPTH_LABELS: Record<string, string> = {
  shallow: '浏览型', moderate: '适中', deep: '深挖型',
};

export function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile()
      .then(setProfile)
      .catch((err) => console.error('Failed to load profile:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.center}>加载中...</div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div style={styles.container}>
        <div style={styles.center}>
          <p style={styles.emptyTitle}>暂无学习画像</p>
          <p style={styles.emptyHint}>对话过程中系统会自动分析你的学习特征</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>学习画像</h1>
        <p style={styles.subtitle}>基于对话内容自动生成</p>
      </div>

      <div style={styles.body}>
        {profile.interests.length > 0 && (
          <div style={styles.card}>
            <div style={styles.cardTitle}>兴趣方向</div>
            <div style={styles.tags}>
              {profile.interests.map((t) => (
                <span key={t} style={styles.tag}>{t}</span>
              ))}
            </div>
          </div>
        )}

        <div style={styles.row}>
          {profile.learning_style && (
            <div style={styles.card}>
              <div style={styles.cardTitle}>学习风格</div>
              <div style={styles.cardValue}>{STYLE_LABELS[profile.learning_style] || profile.learning_style}</div>
            </div>
          )}
          {profile.cognitive_pattern && (
            <div style={styles.card}>
              <div style={styles.cardTitle}>认知模式</div>
              <div style={styles.cardValue}>{COGNITIVE_LABELS[profile.cognitive_pattern] || profile.cognitive_pattern}</div>
            </div>
          )}
          {profile.depth_preference && (
            <div style={styles.card}>
              <div style={styles.cardTitle}>深度偏好</div>
              <div style={styles.cardValue}>{DEPTH_LABELS[profile.depth_preference] || profile.depth_preference}</div>
            </div>
          )}
        </div>

        {profile.knowledge_level && Object.keys(profile.knowledge_level).length > 0 && (
          <div style={styles.card}>
            <div style={styles.cardTitle}>知识水平</div>
            {Object.entries(profile.knowledge_level).map(([domain, level]) => (
              <div key={domain} style={styles.levelRow}>
                <span style={styles.levelDomain}>{domain}</span>
                <div style={styles.levelBar}>
                  <div style={{ ...styles.levelFill, width: `${level}%` }} />
                </div>
                <span style={styles.levelValue}>{level}</span>
              </div>
            ))}
          </div>
        )}

        {profile.learning_goals.length > 0 && (
          <div style={styles.card}>
            <div style={styles.cardTitle}>学习目标</div>
            {profile.learning_goals.map((g) => (
              <div key={g} style={styles.goalItem}>· {g}</div>
            ))}
          </div>
        )}

        {profile.knowledge_gaps.length > 0 && (
          <div style={styles.card}>
            <div style={styles.cardTitle}>知识薄弱点</div>
            <div style={styles.tags}>
              {profile.knowledge_gaps.map((g) => (
                <span key={g} style={{ ...styles.tag, backgroundColor: '#c4a8a0', color: '#5a3e38' }}>{g}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    height: '100vh',
    overflowY: 'auto',
    backgroundColor: '#f5f0eb',
  },
  center: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#a09890',
  },
  emptyTitle: { fontSize: 16, fontWeight: 600, color: '#8a8078', margin: 0 },
  emptyHint: { fontSize: 13, marginTop: 8 },
  header: {
    padding: '20px 24px',
    borderBottom: '1px solid #d5ccc3',
    backgroundColor: '#eae3db',
  },
  title: { fontSize: 20, fontWeight: 700, color: '#4a443d', margin: 0 },
  subtitle: { fontSize: 13, color: '#8a8078', marginTop: 4 },
  body: { padding: 20, display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 700, margin: '0 auto' },
  row: { display: 'flex', gap: 16, flexWrap: 'wrap' as const },
  card: {
    backgroundColor: '#eae3db',
    borderRadius: 10,
    padding: 16,
    border: '1px solid #d5ccc3',
    flex: 1,
    minWidth: 180,
  },
  cardTitle: { fontSize: 12, color: '#8a8078', fontWeight: 600, marginBottom: 8 },
  cardValue: { fontSize: 15, color: '#4a443d', fontWeight: 500 },
  tags: { display: 'flex', flexWrap: 'wrap' as const, gap: 6 },
  tag: {
    padding: '3px 10px',
    backgroundColor: '#c8bfb5',
    borderRadius: 12,
    fontSize: 12,
    color: '#58524a',
  },
  levelRow: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 },
  levelDomain: { width: 40, fontSize: 12, color: '#8a8078' },
  levelBar: { flex: 1, height: 6, backgroundColor: '#d5ccc3', borderRadius: 3, overflow: 'hidden' },
  levelFill: { height: '100%', backgroundColor: '#7a8b8f', borderRadius: 3 },
  levelValue: { width: 30, textAlign: 'right' as const, fontSize: 12, color: '#8a8078' },
  goalItem: { color: '#4a443d', fontSize: 13, marginBottom: 4 },
};

import { useState, useEffect } from 'react';
import { fetchProfile } from '../lib/api';
import type { UserProfile } from '../types';

export function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile()
      .then(setProfile)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div style={styles.container}><div style={styles.center}>加载中...</div></div>;
  }

  if (!profile || (!profile.learningStyle && !profile.cognitivePattern && !profile.knowledgeLevel)) {
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
        {profile.interests && profile.interests.length > 0 && (
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
          {profile.learningStyle && (
            <div style={styles.card}>
              <div style={styles.cardTitle}>学习风格</div>
              <div style={styles.cardValue}>{profile.learningStyle}</div>
            </div>
          )}
          {profile.cognitivePattern && (
            <div style={styles.card}>
              <div style={styles.cardTitle}>认知模式</div>
              <div style={styles.cardValue}>{profile.cognitivePattern}</div>
            </div>
          )}
          {profile.knowledgeLevel && (
            <div style={styles.card}>
              <div style={styles.cardTitle}>知识水平</div>
              <div style={styles.cardValue}>{profile.knowledgeLevel}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, height: '100vh', overflowY: 'auto', backgroundColor: '#f5f0eb' },
  center: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#a09890' },
  emptyTitle: { fontSize: 16, fontWeight: 600, color: '#8a8078', margin: 0 },
  emptyHint: { fontSize: 13, marginTop: 8 },
  header: { padding: '20px 24px', borderBottom: '1px solid #d5ccc3', backgroundColor: '#eae3db' },
  title: { fontSize: 20, fontWeight: 700, color: '#4a443d', margin: 0 },
  subtitle: { fontSize: 13, color: '#8a8078', marginTop: 4 },
  body: { padding: 20, display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 700, margin: '0 auto' },
  row: { display: 'flex', gap: 16, flexWrap: 'wrap' as const },
  card: {
    backgroundColor: '#eae3db', borderRadius: 10, padding: 16,
    border: '1px solid #d5ccc3', flex: 1, minWidth: 180,
  },
  cardTitle: { fontSize: 12, color: '#8a8078', fontWeight: 600, marginBottom: 8 },
  cardValue: { fontSize: 15, color: '#4a443d', fontWeight: 500 },
  tags: { display: 'flex', flexWrap: 'wrap' as const, gap: 6 },
  tag: {
    padding: '3px 10px', backgroundColor: '#c8bfb5', borderRadius: 12,
    fontSize: 12, color: '#58524a',
  },
};

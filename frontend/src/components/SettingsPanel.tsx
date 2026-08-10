import { useState, useEffect } from 'react';
import { fetchSettings, updateSettings, testLLMConnection } from '../lib/api';
import type { LLMProvider } from '../types';

interface ProviderPreset {
  name: string;
  provider: string;
  base_url: string;
  model: string;
  api_mode: string;
  suggestedModels?: string[];
}

const PROVIDER_PRESETS: Record<string, ProviderPreset> = {
  deepseek: {
    name: 'DeepSeek', provider: 'deepseek',
    base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat', api_mode: 'openai',
    suggestedModels: ['deepseek-chat', 'deepseek-reasoner'],
  },
  qwen: {
    name: '通义千问', provider: 'qwen',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus', api_mode: 'openai',
    suggestedModels: ['qwen-plus', 'qwen-turbo', 'qwen-max', 'qwen-long'],
  },
  kimi: {
    name: 'Kimi', provider: 'kimi',
    base_url: 'https://api.moonshot.cn/v1', model: 'moonshot-v1-8k', api_mode: 'openai',
    suggestedModels: ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
  },
  'kimi-cn': {
    name: 'Kimi (国内)', provider: 'kimi-cn',
    base_url: 'https://api.moonshot.cn/v1', model: 'moonshot-v1-8k', api_mode: 'openai',
    suggestedModels: ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
  },
  zhipu: {
    name: '智谱 GLM', provider: 'zhipu',
    base_url: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4-flash', api_mode: 'openai',
    suggestedModels: ['glm-4-flash', 'glm-4-plus', 'glm-4-long'],
  },
  minimax: {
    name: 'MiniMax', provider: 'minimax',
    base_url: 'https://api.minimax.chat/v1', model: 'MiniMax-Text-01', api_mode: 'openai',
    suggestedModels: ['MiniMax-Text-01', 'abab6.5-chat'],
  },
  'minimax-cn': {
    name: 'MiniMax (国内)', provider: 'minimax-cn',
    base_url: 'https://api.minimax.chat/v1', model: 'MiniMax-Text-01', api_mode: 'openai',
    suggestedModels: ['MiniMax-Text-01', 'abab6.5-chat'],
  },
  bailian: {
    name: '阿里百炼', provider: 'bailian',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus', api_mode: 'openai',
    suggestedModels: ['qwen-plus', 'qwen-turbo', 'qwen-max'],
  },
  mimo: {
    name: '小米 MiMo', provider: 'mimo',
    base_url: 'https://api.xiaomi.com/v1', model: 'MiMo-v2-flash', api_mode: 'openai',
    suggestedModels: ['MiMo-v2-flash', 'MiMo-v2-pro'],
  },
  volcengine: {
    name: '火山引擎', provider: 'volcengine',
    base_url: 'https://ark.cn-beijing.volces.com/api/v3', model: 'Doubao-pro-32k', api_mode: 'openai',
    suggestedModels: ['Doubao-pro-32k', 'Doubao-lite-32k', 'Doubao-pro-128k'],
  },
  groq: {
    name: 'Groq', provider: 'groq',
    base_url: 'https://api.groq.com/openai/v1', model: 'llama-3.3-70b-versatile', api_mode: 'openai',
    suggestedModels: ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768', 'gemma2-9b-it'],
  },
  xai: {
    name: 'xAI (Grok)', provider: 'xai',
    base_url: 'https://api.x.ai/v1', model: 'grok-3', api_mode: 'openai',
    suggestedModels: ['grok-3', 'grok-3-mini'],
  },
  nvidia: {
    name: 'NVIDIA NIM', provider: 'nvidia',
    base_url: 'https://integrate.api.nvidia.com/v1', model: 'meta/llama-3.3-70b-instruct', api_mode: 'openai',
    suggestedModels: ['meta/llama-3.3-70b-instruct', 'nvidia/llama-3.1-nemotron-70b-instruct'],
  },
  gemini: {
    name: 'Google Gemini', provider: 'gemini',
    base_url: 'https://generativelanguage.googleapis.com/v1beta/openai', model: 'gemini-2.0-flash', api_mode: 'openai',
    suggestedModels: ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-2.5-pro'],
  },
  azure: {
    name: 'Azure OpenAI', provider: 'azure',
    base_url: 'https://YOUR_RESOURCE.openai.azure.com/openai/deployments/YOUR_DEPLOYMENT', model: 'gpt-4o', api_mode: 'openai',
    suggestedModels: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
  },
  openai: {
    name: 'OpenAI', provider: 'openai',
    base_url: 'https://api.openai.com/v1', model: 'gpt-4o-mini', api_mode: 'openai',
    suggestedModels: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'o1-mini'],
  },
  claude: {
    name: 'Claude', provider: 'claude',
    base_url: 'https://api.anthropic.com/v1', model: 'claude-sonnet-4-20250514', api_mode: 'anthropic',
    suggestedModels: ['claude-sonnet-4-20250514', 'claude-haiku-4-20250514'],
  },
  ollama: {
    name: 'Ollama 本地', provider: 'ollama',
    base_url: 'http://localhost:11434/v1', model: 'qwen2.5:7b', api_mode: 'openai',
    suggestedModels: ['qwen2.5:7b', 'llama3.2:3b', 'deepseek-r1:7b', 'gemma2:9b'],
  },
  custom: {
    name: '自定义', provider: 'custom',
    base_url: '', model: '', api_mode: 'openai',
  },
};

export function SettingsPanel() {
  const [providers, setProviders] = useState<Record<string, LLMProvider>>({});
  const [activeId, setActiveId] = useState('');
  const [testResults, setTestResults] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [multimodalModel, setMultimodalModel] = useState('');

  useEffect(() => {
    fetchSettings().then((s) => {
      setProviders(s.llmProviders || {});
      setActiveId(s.activeProviderId || '');
      setMultimodalModel(s.multimodalModel || '');
    }).catch(console.error);
  }, []);

  const handleAddProvider = (presetKey: string) => {
    const preset = PROVIDER_PRESETS[presetKey];
    const id = `provider_${Date.now()}`;
    const newProvider: LLMProvider = {
      id,
      name: preset.name,
      provider: preset.provider,
      api_key: '',
      base_url: preset.base_url,
      model: preset.model,
      max_tokens: 4096,
      temperature: 0.7,
      api_mode: preset.api_mode,
    };
    setProviders((prev) => ({ ...prev, [id]: newProvider }));
    if (!activeId) setActiveId(id);
    setExpandedId(id);
  };

  const handleUpdateProvider = (id: string, field: string, value: any) => {
    setProviders((prev) => ({
      ...prev,
      [id]: { ...prev[id], [field]: value },
    }));
  };

  const handleTest = async (id: string) => {
    const provider = providers[id];
    if (!provider) return;
    setTestResults((prev) => ({ ...prev, [id]: '测试中...' }));
    try {
      const result = await testLLMConnection(provider);
      setTestResults((prev) => ({
        ...prev,
        [id]: result.success ? `成功: ${result.data?.message}` : `失败: ${result.error}`,
      }));
    } catch (e: any) {
      setTestResults((prev) => ({ ...prev, [id]: `错误: ${e.message}` }));
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateSettings({
        llmProviders: providers,
        activeProviderId: activeId,
        multimodalModel,
      });
      setTestResults({ _saved: '已保存' });
    } catch (e: any) {
      setTestResults({ _saved: `保存失败: ${e.message}` });
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveProvider = (id: string) => {
    setProviders((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    if (activeId === id) setActiveId('');
    if (expandedId === id) setExpandedId(null);
  };

  const presetKeys = Object.keys(PROVIDER_PRESETS);
  const cnPresets = presetKeys.filter(k => ['deepseek', 'qwen', 'kimi', 'kimi-cn', 'zhipu', 'minimax', 'minimax-cn', 'bailian', 'mimo', 'volcengine'].includes(k));
  const intlPresets = presetKeys.filter(k => ['openai', 'claude', 'gemini', 'azure', 'groq', 'xai', 'nvidia'].includes(k));
  const otherPresets = presetKeys.filter(k => ['ollama', 'custom'].includes(k));

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>设置</h2>

      <h3 style={styles.section}>LLM 模型配置</h3>
      <p style={styles.desc}>配置 AI 模型，支持多个厂商切换。选择预设后填入 API Key 即可使用。</p>

      {/* 国内厂商 */}
      <div style={styles.presetGroup}>
        <span style={styles.presetGroupLabel}>国内厂商</span>
        <div style={styles.presets}>
          {cnPresets.map((key) => (
            <button key={key} style={styles.presetBtn} onClick={() => handleAddProvider(key)}>
              + {PROVIDER_PRESETS[key].name}
            </button>
          ))}
        </div>
      </div>

      {/* 国际厂商 */}
      <div style={styles.presetGroup}>
        <span style={styles.presetGroupLabel}>国际厂商</span>
        <div style={styles.presets}>
          {intlPresets.map((key) => (
            <button key={key} style={styles.presetBtn} onClick={() => handleAddProvider(key)}>
              + {PROVIDER_PRESETS[key].name}
            </button>
          ))}
        </div>
      </div>

      {/* 其他 */}
      <div style={styles.presetGroup}>
        <span style={styles.presetGroupLabel}>其他</span>
        <div style={styles.presets}>
          {otherPresets.map((key) => (
            <button key={key} style={styles.presetBtn} onClick={() => handleAddProvider(key)}>
              + {PROVIDER_PRESETS[key].name}
            </button>
          ))}
        </div>
      </div>

      {/* 已配置的提供商 */}
      {Object.entries(providers).map(([id, provider]) => {
        const expanded = expandedId === id;
        const preset = PROVIDER_PRESETS[provider.provider];
        return (
          <div key={id} style={{
            ...styles.providerCard,
            ...(activeId === id ? styles.providerCardActive : {}),
          }}>
            <div style={styles.providerHeader} onClick={() => setExpandedId(expanded ? null : id)}>
              <label style={styles.radioLabel} onClick={(e) => e.stopPropagation()}>
                <input
                  type="radio"
                  name="activeProvider"
                  checked={activeId === id}
                  onChange={() => setActiveId(id)}
                />
                <span style={styles.providerName}>{provider.name}</span>
                {provider.model && <span style={styles.modelBadge}>{provider.model}</span>}
              </label>
              <div style={{ display: 'flex', gap: 6 }}>
                <button style={styles.testBtn} onClick={(e) => { e.stopPropagation(); handleTest(id); }}>
                  测试
                </button>
                <button style={styles.removeBtn} onClick={(e) => { e.stopPropagation(); handleRemoveProvider(id); }}>
                  删除
                </button>
              </div>
            </div>

            {testResults[id] && (
              <div style={styles.testResultLine}>{testResults[id]}</div>
            )}

            {expanded && (
              <div style={styles.fieldGrid}>
                <div style={styles.field}>
                  <label style={styles.label}>API Key</label>
                  <input
                    style={styles.input}
                    type="password"
                    value={provider.api_key}
                    onChange={(e) => handleUpdateProvider(id, 'api_key', e.target.value)}
                    placeholder="sk-..."
                  />
                </div>
                <div style={styles.field}>
                  <label style={styles.label}>API 协议</label>
                  <select
                    style={styles.select}
                    value={provider.api_mode || 'openai'}
                    onChange={(e) => handleUpdateProvider(id, 'api_mode', e.target.value)}
                  >
                    <option value="openai">OpenAI 兼容</option>
                    <option value="anthropic">Anthropic 兼容</option>
                  </select>
                </div>
                <div style={styles.field}>
                  <label style={styles.label}>Base URL</label>
                  <input
                    style={styles.input}
                    value={provider.base_url}
                    onChange={(e) => handleUpdateProvider(id, 'base_url', e.target.value)}
                  />
                </div>
                <div style={styles.field}>
                  <label style={styles.label}>模型</label>
                  <input
                    style={styles.input}
                    value={provider.model}
                    onChange={(e) => handleUpdateProvider(id, 'model', e.target.value)}
                  />
                  {preset?.suggestedModels && (
                    <div style={styles.chips}>
                      {preset.suggestedModels.map((m) => (
                        <button
                          key={m}
                          style={{
                            ...styles.chip,
                            ...(provider.model === m ? styles.chipActive : {}),
                          }}
                          onClick={() => handleUpdateProvider(id, 'model', m)}
                        >
                          {m}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <div style={styles.field}>
                  <label style={styles.label}>Max Tokens</label>
                  <input
                    style={styles.input}
                    type="number"
                    value={provider.max_tokens}
                    onChange={(e) => handleUpdateProvider(id, 'max_tokens', parseInt(e.target.value))}
                  />
                </div>
                <div style={styles.field}>
                  <label style={styles.label}>Temperature</label>
                  <input
                    style={styles.input}
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={provider.temperature}
                    onChange={(e) => handleUpdateProvider(id, 'temperature', parseFloat(e.target.value))}
                  />
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* 多模态模型配置 */}
      <div style={styles.section}>🖼️ 多模态模型（图片描述）</div>
      <p style={styles.desc}>用于 PDF/PPTX/DOCX 中提取的图片自动生成描述，复用当前激活模型的 API Key 和 Base URL</p>
      <div style={{ marginBottom: 16 }}>
        <label style={styles.label}>模型名称</label>
        <input
          style={styles.input}
          value={multimodalModel}
          onChange={(e) => setMultimodalModel(e.target.value)}
          placeholder="如 gpt-4o-mini、qwen-vl-plus（留空则跳过图片描述）"
        />
      </div>

      <div style={styles.footer}>
        <button style={styles.saveBtn} onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '保存设置'}
        </button>
        {testResults._saved && <span style={styles.testResult}>{testResults._saved}</span>}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, padding: 24, maxWidth: 760, margin: '0 auto', overflowY: 'auto', height: '100vh' },
  title: { fontSize: 20, fontWeight: 700, color: '#4a443d', margin: '0 0 16px' },
  section: { fontSize: 16, fontWeight: 600, color: '#4a443d', margin: '16px 0 4px' },
  desc: { fontSize: 13, color: '#8a8078', marginBottom: 12 },
  presetGroup: { marginBottom: 12 },
  presetGroupLabel: { fontSize: 12, color: '#8a8078', fontWeight: 600, marginBottom: 6, display: 'block' },
  presets: { display: 'flex', flexWrap: 'wrap', gap: 6 },
  presetBtn: {
    padding: '5px 10px',
    borderRadius: 6,
    border: '1px solid #c8bfb5',
    backgroundColor: '#f5f0eb',
    color: '#6b5b4f',
    fontSize: 12,
    cursor: 'pointer',
  },
  providerCard: {
    padding: 14,
    backgroundColor: '#eae3db',
    borderRadius: 8,
    border: '2px solid transparent',
    marginBottom: 10,
  },
  providerCardActive: { borderColor: '#7a8b8f' },
  providerHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    cursor: 'pointer',
  },
  radioLabel: { display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' },
  providerName: { fontSize: 14, fontWeight: 600, color: '#4a443d' },
  modelBadge: {
    fontSize: 11, color: '#7a8b8f', backgroundColor: '#f5f0eb',
    padding: '1px 6px', borderRadius: 4,
  },
  testBtn: {
    padding: '3px 10px',
    borderRadius: 4,
    border: '1px solid #c8bfb5',
    backgroundColor: '#f5f0eb',
    color: '#6b5b4f',
    fontSize: 12,
    cursor: 'pointer',
  },
  removeBtn: {
    padding: '3px 10px',
    borderRadius: 4,
    border: '1px solid #c97a6b',
    backgroundColor: 'transparent',
    color: '#c97a6b',
    fontSize: 12,
    cursor: 'pointer',
  },
  testResultLine: {
    fontSize: 12, color: '#6b5b4f', marginTop: 6, padding: '4px 8px',
    backgroundColor: '#f5f0eb', borderRadius: 4,
  },
  fieldGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 },
  field: { display: 'flex', flexDirection: 'column', gap: 4 },
  label: { fontSize: 12, color: '#8a8078' },
  input: {
    padding: '6px 10px',
    border: '1px solid #c8bfb5',
    borderRadius: 4,
    fontSize: 13,
    backgroundColor: '#f5f0eb',
    color: '#4a443d',
    outline: 'none',
  },
  select: {
    padding: '6px 10px',
    border: '1px solid #c8bfb5',
    borderRadius: 4,
    fontSize: 13,
    backgroundColor: '#f5f0eb',
    color: '#4a443d',
    outline: 'none',
  },
  chips: { display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 },
  chip: {
    padding: '2px 8px',
    borderRadius: 10,
    border: '1px solid #d5ccc3',
    backgroundColor: '#f5f0eb',
    color: '#6b5b4f',
    fontSize: 11,
    cursor: 'pointer',
  },
  chipActive: { backgroundColor: '#7a8b8f', color: '#f5f0eb', borderColor: '#7a8b8f' },
  footer: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginTop: 20,
    paddingTop: 16,
    borderTop: '1px solid #d5ccc3',
  },
  saveBtn: {
    padding: '10px 24px',
    backgroundColor: '#7a8b8f',
    color: '#f5f0eb',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
  },
  testResult: { fontSize: 13, color: '#6b5b4f' },
};

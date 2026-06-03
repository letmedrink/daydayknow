export interface Message {
  role: 'user' | 'assistant';
  content: string;
  references?: WikiReference[];
  options?: GuidedOption[];
}

export interface GuidedOption {
  label: string;
  action: string;
}

export interface WikiReference {
  title: string;
  path: string;
}

export interface SSECallbacks {
  onChunk: (content: string) => void;
  onDone: (conversationId: string) => void;
  onOptions: (options: GuidedOption[]) => void;
  onReferences: (references: WikiReference[]) => void;
  onError: (error: Error) => void;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface WikiPage {
  name: string;
  path: string;
  type: string;
  title: string;
  is_dir?: boolean;
  children?: WikiPage[];
}

export interface WikiGraphNode {
  id: string;
  title: string;
  type: string;
  tags: string[];
  path: string;
  linkCount?: number;
  sources?: string[];
}

export interface WikiGraphEdge {
  source: string;
  target: string;
  type: string;
  weight?: number;
}

export interface WikiGraphCommunity {
  id: number;
  nodes: string[];
  size: number;
  cohesion?: number;
  topNodes?: string[];
}

export interface WikiGraph {
  nodes: WikiGraphNode[];
  edges: WikiGraphEdge[];
  communities: WikiGraphCommunity[];
  maxLinks?: number;
}

export interface SurprisingConnection {
  source: string;
  target: string;
  sourceTitle: string;
  targetTitle: string;
  score: number;
  reasons: string[];
}

export interface KnowledgeGap {
  type: 'isolated' | 'sparse_community' | 'bridge';
  nodeId?: string;
  title?: string;
  nodeType?: string;
  communityId?: number;
  size?: number;
  topNodes?: string[];
  connectedCommunities?: number;
  suggestion: string;
  searchQuery: string;
}

export interface GraphInsights {
  surprisingConnections: SurprisingConnection[];
  knowledgeGaps: KnowledgeGap[];
}

export interface SearchResult {
  name: string;
  path: string;
  type: string;
  title: string;
  score: number;
  snippet: string;
}

export interface ReviewItem {
  id: string;
  type: 'contradiction' | 'duplicate' | 'missing-page' | 'suggestion';
  title: string;
  description: string;
  sourcePath?: string;
  affectedPages: string[];
  searchQueries: string[];
  options: { label: string; action: string }[];
  resolved: boolean;
  resolvedAction?: string;
  createdAt: number;
}

export interface LLMProvider {
  id: string;
  name: string;
  provider: string;
  api_key: string;
  base_url: string;
  model: string;
  max_tokens: number;
  temperature: number;
  api_mode?: string; // 'openai' | 'anthropic'
}

export interface AppSettings {
  llmProviders: Record<string, LLMProvider>;
  activeProviderId: string;
  searchApiConfig: Record<string, string>;
  outputLanguage: string;
}

export interface UserProfile {
  learningStyle: string;
  cognitivePattern: string;
  knowledgeLevel: string;
  interests: string[];
  updatedAt: number;
}

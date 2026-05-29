export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface SSECallbacks {
  onChunk: (content: string) => void;
  onDone: (conversationId: string) => void;
  onExtraction: (nodes: KgNode[], edges: KgEdge[]) => void;
  onProfile?: () => void;
  onConflict?: (conflicts: unknown) => void;
  onTaskEnqueued?: (taskId: string, conversationId: string) => void;
  onError: (error: Error) => void;
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface KgNode {
  id: string;
  name: string;
  domain: string | null;
  description: string | null;
  confidence: number;
}

export interface KgEdge {
  id: string;
  from_node_id: string;
  to_node_id: string;
  relation_type: string;
  strength: number;
}

export interface UserProfile {
  knowledge_level: Record<string, number> | null;
  knowledge_gaps: string[];
  interests: string[];
  learning_style: string | null;
  cognitive_pattern: string | null;
  depth_preference: string | null;
  communication_preference: string | null;
  learning_goals: string[];
  misconceptions: string[];
}

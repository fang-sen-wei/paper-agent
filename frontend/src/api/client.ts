const API_BASE = import.meta.env.VITE_API_BASE || '/api';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);

  // 默认走 Vite 的同源 /api 代理；只有 JSON 请求体才补 Content-Type，避免 GET 触发 CORS 预检。
  if (options?.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// 统一从 unknown 错误中提取可展示的信息，避免页面层重复使用 any。
export function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

// Types
export interface DocumentItem {
  id: number;
  filename: string;
  content_type: string;
  file_path: string;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface DocumentUploadResponse {
  message: string;
  documents: DocumentItem[];
}

export interface DocumentProcessResponse {
  message: string;
  document: DocumentItem;
  chunk_count: number;
}

export interface DocumentIndexResponse {
  message: string;
  document_id: number;
  chunk_count: number;
  collection_name: string;
}

export interface DocumentChunkItem {
  id: number;
  document_id: number;
  chunk_index: number;
  page_number: number | null;
  text: string;
  created_at: string;
}

export interface CitationItem {
  index: number;
  chunk_id: number;
  document_id: number;
  filename: string;
  page_number: number | null;
  text_preview: string;
  score: number;
}

export interface SearchResultItem {
  chunk_id: number;
  document_id: number;
  filename: string;
  page_number: number | null;
  text: string;
  score: number;
}

export interface SearchResponse {
  question: string;
  top_k: number;
  results: SearchResultItem[];
  citations: CitationItem[];
}

export interface ChatSessionItem {
  id: number;
  title: string;
  claude_session_id: string | null;
  document_id: number | null;
  web_search_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageItem {
  id: number;
  session_id: number;
  role: string;
  content: string;
  citations: CitationItem[] | null;
  used_web_search: boolean;
  created_at: string;
}

export interface ChatSessionDetailResponse {
  session: ChatSessionItem;
  messages: ChatMessageItem[];
}

export interface ChatMessageCreateResponse {
  session_id: number;
  claude_session_id: string | null;
  question: string;
  answer: string;
  retrieved_count: number;
  citations: CitationItem[];
  used_web_search: boolean;
}

// Health
export const getHealth = () => fetchJson<{ status: string; version: string; name: string; env: string }>('/health');

// Documents
export const uploadDocuments = (files: FileList) => {
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }
  return fetchJson<DocumentUploadResponse>('/documents/upload', { method: 'POST', body: formData });
};

export const listDocuments = () => fetchJson<DocumentItem[]>('/documents/list');

export const deleteDocument = (id: number) => fetchJson<{ message: string }>(`/documents/${id}`, { method: 'DELETE' });

export const processDocument = (id: number) => fetchJson<DocumentProcessResponse>(`/documents/${id}/process`, { method: 'POST' });

export const getDocumentChunks = (id: number) => fetchJson<DocumentChunkItem[]>(`/documents/${id}/chunks`);

export const indexDocument = (id: number) => fetchJson<DocumentIndexResponse>(`/documents/${id}/index`, { method: 'POST' });

export const searchDocuments = (question: string, top_k?: number, document_id?: number) =>
  fetchJson<SearchResponse>('/documents/search', {
    method: 'POST',
    body: JSON.stringify({ question, top_k, document_id }),
  });

// Chat
export const listChatSessions = () => fetchJson<ChatSessionItem[]>('/chat/sessions');

export const createChatSession = (title?: string, document_id?: number | null, web_search_enabled?: boolean) =>
  fetchJson<ChatSessionItem>('/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ title, document_id, web_search_enabled }),
  });

export const getChatSessionDetail = (id: number) => fetchJson<ChatSessionDetailResponse>(`/chat/sessions/${id}`);

export const updateChatSession = (id: number, title: string, document_id: number | null, web_search_enabled: boolean) =>
  fetchJson<ChatSessionItem>(`/chat/sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ title, document_id, web_search_enabled }),
  });

export const deleteChatSession = (id: number) => fetchJson<{ message: string }>(`/chat/sessions/${id}`, { method: 'DELETE' });

export const sendChatMessage = (sessionId: number, question: string, top_k?: number, document_id?: number, web_search_enabled?: boolean) =>
  fetchJson<ChatMessageCreateResponse>(`/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ question, top_k, document_id, web_search_enabled }),
  });

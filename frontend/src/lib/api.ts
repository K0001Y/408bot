const API_BASE = "/api";

const DEFAULT_TIMEOUT = 30_000; // 30s
const LLM_TIMEOUT = 120_000;   // 120s for LLM requests

/** 统一错误消息映射 */
function mapError(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return "请求超时，请稍后重试";
  }
  if (error instanceof TypeError && error.message === "Failed to fetch") {
    return "网络连接失败，请检查网络";
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "未知错误";
}

async function request<T>(path: string, options?: RequestInit & { timeout?: number }): Promise<T> {
  const url = `${API_BASE}${path}`;
  const timeout = options?.timeout ?? DEFAULT_TIMEOUT;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...options?.headers },
      ...options,
      signal: controller.signal,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      if (res.status >= 500) {
        throw new Error(body.message || "服务器内部错误");
      }
      throw new Error(body.message || `请求失败: ${res.status}`);
    }

    return res.json();
  } catch (error) {
    throw new Error(mapError(error));
  } finally {
    clearTimeout(timer);
  }
}

/** 带重试的请求（仅用于 GET/非 POST 请求） */
async function requestWithRetry<T>(path: string, options?: RequestInit & { timeout?: number }): Promise<T> {
  try {
    return await request<T>(path, options);
  } catch (error) {
    // 非 POST 请求重试 1 次
    const method = options?.method?.toUpperCase() ?? "GET";
    if (method !== "POST" && method !== "PUT" && method !== "DELETE") {
      return request<T>(path, options);
    }
    throw error;
  }
}

export const api = {
  // Knowledge
  searchKnowledge: (params: {
    query: string;
    subject?: string;
    chapter?: string;
    content_type?: string;
    top_k?: number;
  }) => request<{ results: SearchResult[]; total: number }>("/knowledge/search", {
    method: "POST",
    body: JSON.stringify(params),
  }),

  getChunk: (id: string) => request<ChunkDetail>(`/knowledge/chunk/${id}`),

  askQuestion: (params: { query: string; subject?: string }) =>
    request<{ answer: string; sources: SearchResult[] }>("/knowledge/ask", {
      method: "POST",
      body: JSON.stringify(params),
      timeout: LLM_TIMEOUT,
    }),

  getChapters: () => requestWithRetry<{ chapters: Record<string, Record<string, string[]>> }>("/knowledge/chapters"),

  // Graph
  getFullGraph: () => requestWithRetry<GraphData>("/graph/"),
  getNodeSubgraph: (nodeId: string, depth?: number) =>
    requestWithRetry<SubgraphData>(`/graph/node/${nodeId}?depth=${depth ?? 2}`),
  searchNodes: (q: string) => requestWithRetry<{ nodes: GraphNode[] }>(`/graph/search?q=${encodeURIComponent(q)}`),

  // Practice
  getExercises: (params?: { subject?: string; chapter?: string; query?: string; top_k?: number }) => {
    const sp = new URLSearchParams();
    if (params?.subject) sp.set("subject", params.subject);
    if (params?.chapter) sp.set("chapter", params.chapter);
    if (params?.query) sp.set("query", params.query);
    if (params?.top_k) sp.set("top_k", String(params.top_k));
    return requestWithRetry<{ exercises: Exercise[]; answers: Exercise[]; total: number }>(`/practice/exercises?${sp}`);
  },

  generateQuiz: (params: {
    topic: string;
    subject?: string;
    quiz_type?: string;
    count?: number;
    difficulty?: string;
  }) => request<QuizResult>("/practice/generate", { method: "POST", body: JSON.stringify(params), timeout: LLM_TIMEOUT }),

  // Exam
  uploadExam: (file: File): Promise<UploadExamResult> => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${API_BASE}/exam/upload`, { method: "POST", body: form })
      .then(r => {
        if (!r.ok) throw new Error(`Upload failed: ${r.status}`);
        return r.json();
      });
  },

  analyzeExam: (params: { question_text: string; subject?: string }) =>
    request<{ answer: string; knowledge_points: string[]; sources: SearchResult[] }>("/exam/analyze", {
      method: "POST",
      body: JSON.stringify(params),
      timeout: LLM_TIMEOUT,
    }),

  // Mistakes
  addMistakes: (params: { input: string; subject_code: string }) =>
    request<{ added: number; mistakes: MistakeItem[] }>("/mistakes/", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  listMistakes: (params?: { subject?: string; chapter?: string }) => {
    const sp = new URLSearchParams();
    if (params?.subject) sp.set("subject", params.subject);
    if (params?.chapter) sp.set("chapter", params.chapter);
    return requestWithRetry<{ mistakes: MistakeItem[]; total: number }>(`/mistakes/?${sp}`);
  },

  deleteMistake: (id: string) => request<{ message: string }>(`/mistakes/${id}`, { method: "DELETE" }),

  updateMistake: (id: string, data: { question_text?: string; answer_text?: string; explanation?: string }) =>
    request<MistakeItem>(`/mistakes/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  generateWord: (ids: string[]) =>
    request<{ filename: string; download_url: string }>("/mistakes/generate-word", {
      method: "POST",
      body: JSON.stringify({ mistake_ids: ids }),
    }),

  // Health
  health: () => requestWithRetry<{ status: string; components: Record<string, boolean> }>("/health"),
};

// Types
export interface SearchResult {
  chunk_id: string;
  subsection?: string;
  subsection_title?: string;
  subject_code?: string;
  chapter_number?: string;
  content_type?: string;
  preview?: string;
  score?: number;
}

export interface ChunkDetail {
  chunk_id: string;
  subject_code?: string;
  chapter_number?: string;
  subsection?: string;
  subsection_title?: string;
  content_type?: string;
  page_start?: number;
  page_end?: number;
  content: string;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  subject_code?: string;
  chapter?: string;
  chunk_id?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  weight?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
}

export interface SubgraphData {
  center_node: string;
  depth: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Exercise {
  chunk_id: string;
  subsection?: string;
  subsection_title?: string;
  subject_code?: string;
  chapter_number?: string;
  content_type?: string;
  content?: string;
  preview?: string;
  score?: number;
}

export interface QuizResult {
  quiz_content: string;
  quiz_type: string;
  count: number;
  difficulty: string;
  sources: SearchResult[];
}

export interface MistakeItem {
  mistake_id: string;
  subject_code: string;
  page: number;
  chapter: string;
  question_number: number;
  question_text: string;
  answer_text: string;
  explanation: string;
  added_at: string;
}

export interface UploadExamResult {
  file_id: string;
  filename: string;
  saved_as: string;
  size: number;
  message: string;
  ocr_text?: string;
  ocr_error?: string | null;
}
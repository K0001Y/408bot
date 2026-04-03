const API_BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || `Request failed: ${res.status}`);
  }

  return res.json();
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
    }),

  getChapters: () => request<{ chapters: Record<string, Record<string, string[]>> }>("/knowledge/chapters"),

  // Graph
  getFullGraph: () => request<GraphData>("/graph/"),
  getNodeSubgraph: (nodeId: string, depth?: number) =>
    request<SubgraphData>(`/graph/node/${nodeId}?depth=${depth ?? 2}`),
  searchNodes: (q: string) => request<{ nodes: GraphNode[] }>(`/graph/search?q=${encodeURIComponent(q)}`),

  // Practice
  getExercises: (params?: { subject?: string; chapter?: string; query?: string; top_k?: number }) => {
    const sp = new URLSearchParams();
    if (params?.subject) sp.set("subject", params.subject);
    if (params?.chapter) sp.set("chapter", params.chapter);
    if (params?.query) sp.set("query", params.query);
    if (params?.top_k) sp.set("top_k", String(params.top_k));
    return request<{ exercises: Exercise[]; answers: Exercise[]; total: number }>(`/practice/exercises?${sp}`);
  },

  generateQuiz: (params: {
    topic: string;
    subject?: string;
    quiz_type?: string;
    count?: number;
    difficulty?: string;
  }) => request<QuizResult>("/practice/generate", { method: "POST", body: JSON.stringify(params) }),

  // Exam
  uploadExam: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${API_BASE}/exam/upload`, { method: "POST", body: form }).then(r => r.json());
  },

  analyzeExam: (params: { question_text: string; subject?: string }) =>
    request<{ answer: string; knowledge_points: string[]; sources: SearchResult[] }>("/exam/analyze", {
      method: "POST",
      body: JSON.stringify(params),
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
    return request<{ mistakes: MistakeItem[]; total: number }>(`/mistakes/?${sp}`);
  },

  deleteMistake: (id: string) => request<{ message: string }>(`/mistakes/${id}`, { method: "DELETE" }),

  generateWord: (ids: string[]) =>
    request<{ filename: string; download_url: string }>("/mistakes/generate-word", {
      method: "POST",
      body: JSON.stringify({ mistake_ids: ids }),
    }),

  // Health
  health: () => request<{ status: string; components: Record<string, boolean> }>("/health"),
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
import { useState, useRef, useEffect } from "react";
import { Search, Send, Loader2, Terminal, ChevronRight, Cpu, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { SubjectPicker } from "@/components/SubjectPicker";
import { api, type SearchResult } from "@/lib/api";
import { getSubjectName } from "@/lib/constants";
import { useLoading } from "@/hooks/useLoading";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SearchResult[];
  thinking?: string;
  intermediate_steps?: Array<{ tool: string; output: string }>;
  is_agentic?: boolean;
}

const EXAMPLE_QUESTIONS = [
  "什么是哈夫曼树？",
  "TCP 三次握手的过程",
  "页面置换算法有哪些？",
  "流水线的基本概念",
];

export function KnowledgePage() {
  const [subject, setSubject] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [mode, setMode] = useState<"search" | "chat">("chat");
  const [expandedThinking, setExpandedThinking] = useState<Set<string>>(new Set());
  const { loading, run } = useLoading();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSearch = async () => {
    if (!query.trim()) return;
    const result = await run(() =>
      api.searchKnowledge({ query: query.trim(), subject: subject ?? undefined, top_k: 10 })
    );
    if (result) setSearchResults(result.results);
  };

  const handleAsk = async () => {
    if (!query.trim() || loading) return;
    const q = query.trim();
    setQuery("");
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);

    const result = await run(() =>
      api.askQuestion({ query: q, subject: subject ?? undefined })
    );
    const assistantMsg: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: result?.answer ?? "抱歉，暂时无法回答该问题。请检查后端服务是否正常运行。",
      sources: result?.sources,
      thinking: result?.thinking,
      intermediate_steps: result?.intermediate_steps,
      is_agentic: result?.is_agentic,
    };
    setMessages((prev) => [...prev, assistantMsg]);
  };

  const toggleThinking = (id: string) => {
    setExpandedThinking((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === "search") handleSearch();
    else handleAsk();
  };

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <header className="flex flex-shrink-0 items-center justify-between border-b border-border bg-card/80 px-6 py-3">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="font-display text-base font-semibold text-foreground tracking-wider">知识库</h1>
            <p className="font-mono-tech text-[9px] text-muted-foreground tracking-widest">KNOWLEDGE BASE</p>
          </div>
          {/* Mode toggle — no rounding */}
          <div className="flex border border-border">
            <button
              onClick={() => setMode("chat")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 font-mono-tech text-[10px] font-medium tracking-widest transition-smooth",
                mode === "chat"
                  ? "bg-accent text-accent-foreground border-r border-primary/30"
                  : "text-muted-foreground hover:text-foreground border-r border-border"
              )}
            >
              <Terminal className="h-3 w-3" />
              QA
            </button>
            <button
              onClick={() => setMode("search")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 font-mono-tech text-[10px] font-medium tracking-widest transition-smooth",
                mode === "search"
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Search className="h-3 w-3" />
              SEARCH
            </button>
          </div>
        </div>
        <SubjectPicker value={subject} onChange={setSubject} />
      </header>

      {/* Content */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 scanlines">
        {mode === "chat" ? (
          <div className="mx-auto max-w-2xl space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-center animate-fade-in-up">
                {/* Terminal-style icon box */}
                <div className="bracket-corners relative mb-5 flex h-16 w-16 items-center justify-center border border-primary/40 bg-card">
                  <Terminal className="h-7 w-7 text-primary" />
                  <div className="hr-amber absolute bottom-0 left-0 right-0" />
                </div>
                <h2 className="font-display mb-2 text-xl font-semibold text-foreground tracking-wider">
                  408 KNOWLEDGE BASE
                </h2>
                <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
                  基于数据结构、操作系统、计算机组成原理、计算机网络四本教材，为你提供精准的知识点解答
                </p>
                {/* Example prompts — rectangular */}
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {EXAMPLE_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => setQuery(q)}
                      className="border border-border bg-card px-3 py-1.5 font-mono-tech text-[10px] text-muted-foreground tracking-wide transition-smooth hover:border-primary/50 hover:bg-accent/30 hover:text-accent-foreground"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  "animate-fade-in",
                  msg.role === "user" ? "flex justify-end" : "flex justify-start items-start gap-2"
                )}
              >
                {/* AI prefix label */}
                {msg.role === "assistant" && (
                  <div className="mt-1 shrink-0">
                    <div className="flex h-6 w-6 items-center justify-center bg-primary shadow-glow">
                      <span className="font-mono-tech text-[8px] font-bold text-primary-foreground">AI</span>
                    </div>
                  </div>
                )}

                <div
                  className={cn(
                    "max-w-[82%] px-4 py-3 text-sm leading-relaxed",
                    msg.role === "user"
                      ? "gradient-primary text-primary-foreground shadow-glow"
                      : "border border-border bg-card text-foreground border-l-2 border-l-primary/40"
                  )}
                >
                  {/* Thinking / Agentic Trace Block */}
                  {msg.role === "assistant" && (msg.thinking || (msg.intermediate_steps && msg.intermediate_steps.length > 0)) && (
                    <div className="mb-3 border border-primary/20 bg-background/40">
                      <button
                        onClick={() => toggleThinking(msg.id)}
                        className="flex w-full items-center gap-2 px-3 py-2 font-mono-tech text-[9px] tracking-widest text-primary/70 hover:text-primary hover:bg-primary/5 transition-smooth"
                      >
                        <ChevronRight
                          className={cn(
                            "h-3 w-3 shrink-0 transition-transform duration-200",
                            expandedThinking.has(msg.id) && "rotate-90"
                          )}
                        />
                        {msg.is_agentic ? (
                          <><Cpu className="h-3 w-3" /><span>AGENTIC TRACE</span></>
                        ) : (
                          <><Cpu className="h-3 w-3" /><span>THINKING PROCESS</span></>
                        )}
                        <span className="ml-auto opacity-60">
                          {msg.intermediate_steps ? `${msg.intermediate_steps.length} steps` : "1 step"}
                        </span>
                      </button>
                      {expandedThinking.has(msg.id) && (
                        <div className="border-t border-primary/10 px-3 py-2 space-y-2">
                          {msg.thinking && (
                            <div className="font-mono-tech text-[10px] leading-relaxed text-muted-foreground whitespace-pre-wrap">
                              {msg.thinking}
                            </div>
                          )}
                          {msg.intermediate_steps && msg.intermediate_steps.length > 0 && (
                            <div className="space-y-1">
                              {msg.intermediate_steps.map((step, idx) => (
                                <div key={idx} className="flex items-start gap-2 text-[10px]">
                                  <Wrench className="h-3 w-3 shrink-0 mt-0.5 text-primary/50" />
                                  <div>
                                    <span className="font-mono-tech text-primary/70">{step.tool}</span>
                                    <p className="text-muted-foreground line-clamp-2">{step.output}</p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 border-t border-white/10 pt-2">
                      <p className="mb-1.5 font-mono-tech text-[9px] uppercase tracking-widest opacity-50">
                        REFERENCES
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {msg.sources.slice(0, 5).map((s, i) => (
                          <Badge key={i} variant="secondary">
                            {s.subsection} {s.subsection_title}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* USER label */}
                {msg.role === "user" && (
                  <div className="mt-1 shrink-0">
                    <div className="flex h-6 w-6 items-center justify-center bg-secondary border border-border">
                      <span className="font-mono-tech text-[8px] font-bold text-muted-foreground">U</span>
                    </div>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex animate-fade-in items-start gap-2">
                <div className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center bg-primary shadow-glow">
                  <span className="font-mono-tech text-[8px] font-bold text-primary-foreground">AI</span>
                </div>
                <div className="border border-border border-l-2 border-l-primary/40 bg-card px-4 py-3 text-sm text-muted-foreground">
                  <span className="font-mono-tech text-xs">
                    PROCESSING
                    <span className="animate-typing inline-block ml-0.5" style={{ animationDelay: "0ms" }}>.</span>
                    <span className="animate-typing inline-block" style={{ animationDelay: "200ms" }}>.</span>
                    <span className="animate-typing inline-block" style={{ animationDelay: "400ms" }}>.</span>
                  </span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="mx-auto max-w-2xl space-y-2">
            {searchResults.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center animate-fade-in-up">
                <Search className="mb-3 h-10 w-10 text-muted-foreground/20" />
                <p className="font-mono-tech text-sm text-muted-foreground tracking-widest">INPUT SEARCH QUERY</p>
              </div>
            ) : (
              searchResults.map((r, idx) => (
                <div
                  key={r.chunk_id}
                  className="animate-fade-in border border-border bg-card/80 p-4 transition-smooth hover:border-primary/40 hover:shadow-glow bracket-corners"
                  style={{ animationDelay: `${idx * 40}ms` }}
                >
                  <div className="mb-2 flex items-center gap-2 flex-wrap">
                    <Badge variant="default">{getSubjectName(r.subject_code ?? "")}</Badge>
                    <Badge variant="secondary">{r.subsection}</Badge>
                    <span className="font-mono-tech text-[10px] text-muted-foreground">{r.subsection_title}</span>
                    {r.score != null && (
                      <span className="ml-auto font-mono-tech text-[10px] text-primary/80">
                        {(r.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  <p className="line-clamp-3 text-sm leading-relaxed text-foreground/75">{r.preview}</p>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="flex-shrink-0 border-t border-border bg-card/50 px-6 py-4">
        <form onSubmit={handleSubmit} className="mx-auto flex max-w-2xl items-center gap-2">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={mode === "chat" ? "// 输入你的问题..." : "// SEARCH QUERY..."}
            className="flex-1 font-mono-tech text-sm"
            disabled={loading}
          />
          <Button type="submit" size="icon" disabled={loading || !query.trim()} className="shrink-0">
            {loading
              ? <Loader2 className="h-4 w-4 animate-spin" />
              : mode === "chat"
              ? <Send className="h-4 w-4" />
              : <Search className="h-4 w-4" />}
          </Button>
        </form>
      </div>
    </div>
  );
}

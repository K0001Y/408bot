import { useState, useRef, useEffect } from "react";
import { Search, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
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
}

export function KnowledgePage() {
  const [subject, setSubject] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [mode, setMode] = useState<"search" | "chat">("chat");
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
      api.searchKnowledge({
        query: query.trim(),
        subject: subject ?? undefined,
        top_k: 10,
      })
    );
    if (result) {
      setSearchResults(result.results);
    }
  };

  const handleAsk = async () => {
    if (!query.trim() || loading) return;
    const q = query.trim();
    setQuery("");

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: q,
    };
    setMessages((prev) => [...prev, userMsg]);

    const result = await run(() =>
      api.askQuestion({ query: q, subject: subject ?? undefined })
    );

    const assistantMsg: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: result?.answer ?? "抱歉，暂时无法回答该问题。请检查后端服务是否正常运行。",
      sources: result?.sources,
    };
    setMessages((prev) => [...prev, assistantMsg]);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === "search") handleSearch();
    else handleAsk();
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-foreground">知识库</h1>
          <p className="text-xs text-muted-foreground">搜索教材知识点或向 AI 提问</p>
        </div>
        <div className="flex items-center gap-3">
          <SubjectPicker value={subject} onChange={setSubject} />
          <div className="flex rounded-lg border border-border">
            <button
              onClick={() => setMode("chat")}
              className={cn(
                "rounded-l-lg px-3 py-1.5 text-xs font-medium transition-smooth",
                mode === "chat" ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              问答
            </button>
            <button
              onClick={() => setMode("search")}
              className={cn(
                "rounded-r-lg px-3 py-1.5 text-xs font-medium transition-smooth",
                mode === "search" ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              检索
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6">
        {mode === "chat" ? (
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl gradient-primary shadow-glow">
                  <Search className="h-7 w-7 text-primary-foreground" />
                </div>
                <h2 className="mb-2 text-xl font-semibold text-foreground">408 知识问答</h2>
                <p className="max-w-md text-sm text-muted-foreground">
                  基于数据结构、操作系统、计算机组成原理、计算机网络四本教材，
                  为你提供精准的知识点解答
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {["什么是哈夫曼树？", "TCP 三次握手的过程", "页面置换算法有哪些？", "流水线的基本概念"].map((q) => (
                    <button
                      key={q}
                      onClick={() => { setQuery(q); }}
                      className="rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-smooth hover:border-primary/30 hover:text-foreground"
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
                  msg.role === "user" ? "flex justify-end" : "flex justify-start"
                )}
              >
                <div
                  className={cn(
                    "max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed",
                    msg.role === "user"
                      ? "gradient-primary text-primary-foreground"
                      : "bg-secondary text-foreground"
                  )}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 border-t border-border/30 pt-2">
                      <p className="mb-1 text-[10px] uppercase tracking-wider opacity-60">参考来源</p>
                      <div className="flex flex-wrap gap-1">
                        {msg.sources.slice(0, 5).map((s, i) => (
                          <Badge key={i} variant="secondary" className="text-[10px]">
                            {s.subsection} {s.subsection_title}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start animate-fade-in">
                <div className="flex items-center gap-2 rounded-xl bg-secondary px-4 py-3 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  正在思考...
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-3">
            {searchResults.length === 0 ? (
              <p className="py-20 text-center text-sm text-muted-foreground">输入关键词搜索教材知识点</p>
            ) : (
              searchResults.map((r) => (
                <Card key={r.chunk_id} className="transition-smooth hover:border-primary/30">
                  <CardContent className="p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <Badge variant="default">{getSubjectName(r.subject_code ?? "")}</Badge>
                      <Badge variant="secondary">{r.subsection}</Badge>
                      <span className="text-xs text-muted-foreground">{r.subsection_title}</span>
                      {r.score != null && (
                        <span className="ml-auto text-[10px] text-muted-foreground">
                          {(r.score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed text-foreground/80 line-clamp-3">{r.preview}</p>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-border p-4">
        <form onSubmit={handleSubmit} className="mx-auto flex max-w-3xl items-center gap-2">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={mode === "chat" ? "输入你的问题..." : "输入关键词搜索..."}
            className="flex-1"
            disabled={loading}
          />
          <Button type="submit" size="icon" disabled={loading || !query.trim()}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : mode === "chat" ? <Send className="h-4 w-4" /> : <Search className="h-4 w-4" />}
          </Button>
        </form>
      </div>
    </div>
  );
}
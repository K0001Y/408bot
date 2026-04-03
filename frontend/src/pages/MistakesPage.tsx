import { useState, useEffect } from "react";
import { Plus, Trash2, Download, Loader2, BookMarked } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { SubjectPicker } from "@/components/SubjectPicker";
import { api, type MistakeItem } from "@/lib/api";
import { getSubjectShort } from "@/lib/constants";
import { useLoading } from "@/hooks/useLoading";
import { cn } from "@/lib/utils";

export function MistakesPage() {
  const [subject, setSubject] = useState<string | null>(null);
  const [mistakes, setMistakes] = useState<MistakeItem[]>([]);
  const [inputText, setInputText] = useState("");
  const [addSubject, setAddSubject] = useState("ds");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const listLoader = useLoading();
  const addLoader = useLoading();
  const exportLoader = useLoading();

  const fetchMistakes = async () => {
    const result = await listLoader.run(() =>
      api.listMistakes({ subject: subject ?? undefined })
    );
    if (result) setMistakes(result.mistakes);
  };

  useEffect(() => { fetchMistakes(); }, [subject]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    const result = await addLoader.run(() =>
      api.addMistakes({ input: inputText.trim(), subject_code: addSubject })
    );
    if (result) { setInputText(""); fetchMistakes(); }
  };

  const handleDelete = async (id: string) => {
    await api.deleteMistake(id);
    setMistakes((prev) => prev.filter((m) => m.mistake_id !== id));
    setSelectedIds((prev) => { const next = new Set(prev); next.delete(id); return next; });
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === mistakes.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(mistakes.map((m) => m.mistake_id)));
  };

  const handleExport = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    const result = await exportLoader.run(() => api.generateWord(ids));
    if (result?.download_url) window.open(result.download_url, "_blank");
  };

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <header className="flex flex-shrink-0 items-center justify-between border-b border-border bg-card/50 px-6 py-3">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="font-display text-base font-semibold text-foreground tracking-wide">错题本</h1>
            <p className="font-mono-tech text-[10px] text-muted-foreground tracking-widest">
              {mistakes.length > 0 ? `${mistakes.length} MISTAKES` : "MISTAKE BOOK"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <SubjectPicker value={subject} onChange={setSubject} />
          {selectedIds.size > 0 && (
            <Button onClick={handleExport} variant="amber" size="sm" disabled={exportLoader.loading}>
              {exportLoader.loading
                ? <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                : <Download className="mr-1.5 h-3 w-3" />}
              EXPORT ({selectedIds.size})
            </Button>
          )}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-2xl space-y-5">
          {/* Add form */}
          <div className="animate-scale-in border border-border bg-card/80 overflow-hidden">
            <div className="flex items-center gap-2.5 border-b border-border bg-card/60 px-5 py-3 scanlines">
              <div className="flex h-7 w-7 items-center justify-center bg-primary/10 border border-primary/20">
                <Plus className="h-3.5 w-3.5 text-primary" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground tracking-wide">添加错题</p>
                <p className="font-mono-tech text-[10px] text-muted-foreground tracking-widest">ADD MISTAKE</p>
              </div>
            </div>
            <div className="p-5">
              <form onSubmit={handleAdd} className="space-y-3">
                <div>
                  <label className="mb-1.5 block font-mono-tech text-[10px] text-muted-foreground uppercase tracking-widest">
                    // 格式：页码 章节 题号1 题号2 ...（如 156 3.4 5 6 7）
                  </label>
                  <Input
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="156 3.4 5 6 7"
                    disabled={addLoader.loading}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono-tech text-[11px] text-muted-foreground tracking-widest">SUBJECT:</span>
                    <SubjectPicker
                      value={addSubject}
                      onChange={(v) => v && setAddSubject(v)}
                      showAll={false}
                    />
                  </div>
                  <Button type="submit" size="sm" disabled={addLoader.loading || !inputText.trim()}>
                    {addLoader.loading
                      ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                      : <Plus className="mr-1.5 h-3.5 w-3.5" />}
                    ADD
                  </Button>
                </div>
                {addLoader.error && (
                  <p className="font-mono-tech text-xs text-destructive">{addLoader.error}</p>
                )}
              </form>
            </div>
          </div>

          {/* Mistake list */}
          {mistakes.length > 0 && (
            <div>
              <div className="mb-3 flex items-center justify-between">
                <button
                  onClick={selectAll}
                  className="flex items-center gap-2 font-mono-tech text-[11px] text-muted-foreground tracking-widest transition-smooth hover:text-foreground"
                >
                  {/* Square checkbox indicator */}
                  <div className={cn(
                    "flex h-3.5 w-3.5 items-center justify-center border transition-smooth",
                    selectedIds.size === mistakes.length && mistakes.length > 0
                      ? "border-primary bg-primary"
                      : "border-muted-foreground/40"
                  )}>
                    {selectedIds.size === mistakes.length && mistakes.length > 0 && (
                      <svg className="h-2 w-2 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="square" strokeLinejoin="miter" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                  {selectedIds.size === mistakes.length ? "DESELECT ALL" : "SELECT ALL"}
                </button>
                <span className="font-mono-tech text-[10px] text-muted-foreground/50">
                  {selectedIds.size > 0 ? `${selectedIds.size} SELECTED` : ""}
                </span>
              </div>
              <div className="space-y-1.5">
                {mistakes.map((m, idx) => (
                  <div
                    key={m.mistake_id}
                    onClick={() => toggleSelect(m.mistake_id)}
                    className={cn(
                      "animate-fade-in group relative flex cursor-pointer items-start gap-3 border p-4 transition-smooth",
                      selectedIds.has(m.mistake_id)
                        ? "border-primary/40 bg-accent/20 border-l-2 border-l-primary"
                        : "border-border bg-card/60 hover:border-border/80 hover:bg-card/80"
                    )}
                    style={{ animationDelay: `${idx * 20}ms` }}
                  >
                    {/* Square checkbox */}
                    <div
                      className={cn(
                        "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center border transition-smooth",
                        selectedIds.has(m.mistake_id)
                          ? "border-primary bg-primary"
                          : "border-muted-foreground/30"
                      )}
                    >
                      {selectedIds.has(m.mistake_id) && (
                        <svg className="h-2.5 w-2.5 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="square" strokeLinejoin="miter" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>

                    {/* Content */}
                    <div className="min-w-0 flex-1">
                      <div className="mb-1.5 flex items-center gap-2 flex-wrap">
                        <Badge variant="default" className="font-mono-tech text-[10px]">
                          {getSubjectShort(m.subject_code)}
                        </Badge>
                        <span className="text-sm font-medium text-foreground">
                          第{m.chapter}章 · P{m.page} · 第{m.question_number}题
                        </span>
                        {m.added_at && (
                          <span className="ml-auto font-mono-tech text-[10px] text-muted-foreground/50">
                            {m.added_at}
                          </span>
                        )}
                      </div>
                      {m.answer_text && (
                        <p className="line-clamp-2 font-mono-tech text-xs leading-relaxed text-muted-foreground">
                          {m.answer_text.slice(0, 150)}...
                        </p>
                      )}
                    </div>

                    {/* Delete button */}
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(m.mistake_id); }}
                      className="shrink-0 p-1.5 text-muted-foreground/40 opacity-0 transition-smooth group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty state */}
          {mistakes.length === 0 && !listLoader.loading && (
            <div className="flex flex-col items-center justify-center py-20 text-center animate-fade-in-up">
              <div className="bracket-corners relative mb-4 flex h-14 w-14 items-center justify-center border border-border bg-card">
                <BookMarked className="h-6 w-6 text-muted-foreground/30" />
              </div>
              <p className="font-mono-tech text-[11px] font-medium text-muted-foreground tracking-widest">
                // NO MISTAKES RECORDED
              </p>
              <p className="mt-1 font-mono-tech text-[10px] text-muted-foreground/50 tracking-wider">
                在上方添加做错的题目，方便复习
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect } from "react";
import { Plus, Trash2, Download, Loader2, BookMarked } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
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
    if (result) {
      setMistakes(result.mistakes);
    }
  };

  useEffect(() => {
    fetchMistakes();
  }, [subject]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    const result = await addLoader.run(() =>
      api.addMistakes({ input: inputText.trim(), subject_code: addSubject })
    );
    if (result) {
      setInputText("");
      fetchMistakes();
    }
  };

  const handleDelete = async (id: string) => {
    await api.deleteMistake(id);
    setMistakes((prev) => prev.filter((m) => m.mistake_id !== id));
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === mistakes.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(mistakes.map((m) => m.mistake_id)));
    }
  };

  const handleExport = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;

    const result = await exportLoader.run(() => api.generateWord(ids));
    if (result?.download_url) {
      window.open(result.download_url, "_blank");
    }
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-foreground">错题本</h1>
          <p className="text-xs text-muted-foreground">
            {mistakes.length > 0 ? `共 ${mistakes.length} 道错题` : "记录做错的题目，导出 Word 复习"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <SubjectPicker value={subject} onChange={setSubject} />
          {selectedIds.size > 0 && (
            <Button onClick={handleExport} variant="amber" size="sm" disabled={exportLoader.loading}>
              {exportLoader.loading ? <Loader2 className="mr-1.5 h-3 w-3 animate-spin" /> : <Download className="mr-1.5 h-3 w-3" />}
              导出 Word ({selectedIds.size})
            </Button>
          )}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {/* Add form */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Plus className="h-4 w-4 text-primary" />
                添加错题
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleAdd} className="flex items-end gap-3">
                <div className="flex-1">
                  <label className="mb-1 block text-xs text-muted-foreground">
                    格式: 页码 章节 题号1 题号2 ...（如 156 3.4 5 6 7）
                  </label>
                  <Input
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="156 3.4 5 6 7"
                    disabled={addLoader.loading}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-muted-foreground">科目</label>
                  <SubjectPicker value={addSubject} onChange={(v) => v && setAddSubject(v)} showAll={false} />
                </div>
                <Button type="submit" size="sm" disabled={addLoader.loading || !inputText.trim()}>
                  {addLoader.loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                </Button>
              </form>
              {addLoader.error && (
                <p className="mt-2 text-xs text-destructive">{addLoader.error}</p>
              )}
            </CardContent>
          </Card>

          {/* Mistake list */}
          {mistakes.length > 0 && (
            <div>
              <div className="mb-3 flex items-center justify-between">
                <button onClick={selectAll} className="text-xs text-muted-foreground hover:text-foreground transition-smooth">
                  {selectedIds.size === mistakes.length ? "取消全选" : "全选"}
                </button>
              </div>
              <div className="space-y-2">
                {mistakes.map((m) => (
                  <Card
                    key={m.mistake_id}
                    className={cn(
                      "transition-smooth cursor-pointer",
                      selectedIds.has(m.mistake_id) ? "border-primary/40 shadow-glow" : "hover:border-border/80"
                    )}
                    onClick={() => toggleSelect(m.mistake_id)}
                  >
                    <CardContent className="flex items-start gap-3 p-4">
                      {/* Checkbox */}
                      <div
                        className={cn(
                          "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-smooth",
                          selectedIds.has(m.mistake_id)
                            ? "border-primary bg-primary"
                            : "border-muted-foreground/30"
                        )}
                      >
                        {selectedIds.has(m.mistake_id) && (
                          <svg className="h-2.5 w-2.5 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>

                      {/* Content */}
                      <div className="min-w-0 flex-1">
                        <div className="mb-1 flex items-center gap-2">
                          <Badge variant="default">{getSubjectShort(m.subject_code)}</Badge>
                          <span className="text-sm font-medium text-foreground">
                            第{m.chapter}章 P{m.page} 第{m.question_number}题
                          </span>
                          {m.added_at && (
                            <span className="ml-auto text-[10px] text-muted-foreground">{m.added_at}</span>
                          )}
                        </div>
                        {m.answer_text && (
                          <p className="text-xs leading-relaxed text-muted-foreground line-clamp-2">
                            {m.answer_text.slice(0, 150)}...
                          </p>
                        )}
                      </div>

                      {/* Delete */}
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(m.mistake_id); }}
                        className="shrink-0 rounded-md p-1 text-muted-foreground transition-smooth hover:bg-destructive/10 hover:text-destructive"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {mistakes.length === 0 && !listLoader.loading && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <BookMarked className="mb-3 h-12 w-12 text-muted-foreground/30" />
              <p className="text-sm text-muted-foreground">暂无错题记录</p>
              <p className="text-xs text-muted-foreground/60">在上方添加做错的题目，方便复习</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
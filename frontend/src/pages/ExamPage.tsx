import { useState, useRef } from "react";
import { Upload, Send, Loader2, FileText, X, Tag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { SubjectPicker } from "@/components/SubjectPicker";
import { api } from "@/lib/api";
import { useLoading } from "@/hooks/useLoading";

export function ExamPage() {
  const [subject, setSubject] = useState<string | null>(null);
  const [questionText, setQuestionText] = useState("");
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [result, setResult] = useState<{ answer: string; knowledge_points: string[] } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const uploadLoader = useLoading();
  const analyzeLoader = useLoading();

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const res = await uploadLoader.run(() => api.uploadExam(file));
    if (res) setUploadedFile(res.filename || file.name);
  };

  const handleAnalyze = async () => {
    if (!questionText.trim()) return;
    const res = await analyzeLoader.run(() =>
      api.analyzeExam({ question_text: questionText.trim(), subject: subject ?? undefined })
    );
    if (res) setResult({ answer: res.answer, knowledge_points: res.knowledge_points });
  };

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <header className="flex flex-shrink-0 items-center justify-between border-b border-border bg-card/50 px-6 py-3">
        <div>
          <h1 className="font-display text-base font-semibold text-foreground tracking-wide">真题坊</h1>
          <p className="font-mono-tech text-[10px] text-muted-foreground tracking-widest">EXAM ANALYSIS</p>
        </div>
        <SubjectPicker value={subject} onChange={setSubject} showAll={false} />
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-2xl space-y-4">
          {/* Upload zone */}
          <div className="animate-scale-in border border-border bg-card/80 overflow-hidden">
            <div className="flex items-center gap-2.5 border-b border-border bg-card/60 px-5 py-3 scanlines">
              <div className="flex h-7 w-7 items-center justify-center bg-primary/10 border border-primary/20">
                <Upload className="h-3.5 w-3.5 text-primary" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground tracking-wide">上传真题（可选）</p>
                <p className="font-mono-tech text-[10px] text-muted-foreground tracking-widest">UPLOAD EXAM PAPER</p>
              </div>
            </div>
            <div className="p-5">
              <input
                ref={fileRef}
                type="file"
                accept=".png,.jpg,.jpeg,.pdf"
                className="hidden"
                onChange={handleUpload}
              />
              {uploadedFile ? (
                <div className="flex items-center gap-3 border border-primary/20 bg-accent/20 px-4 py-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center gradient-primary">
                    <FileText className="h-4 w-4 text-primary-foreground" />
                  </div>
                  <span className="flex-1 truncate font-mono-tech text-sm font-medium text-foreground">{uploadedFile}</span>
                  <button
                    onClick={() => setUploadedFile(null)}
                    className="text-muted-foreground transition-smooth hover:text-destructive"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => fileRef.current?.click()}
                  disabled={uploadLoader.loading}
                  className="group relative flex w-full flex-col items-center justify-center gap-3 border-2 border-dashed border-border py-10 transition-smooth hover:border-primary/40 hover:bg-accent/10"
                >
                  {/* Bracket corner decorations on hover */}
                  <span className="pointer-events-none absolute left-2 top-2 h-4 w-4 border-l border-t border-primary/0 transition-smooth group-hover:border-primary/60" />
                  <span className="pointer-events-none absolute right-2 top-2 h-4 w-4 border-r border-t border-primary/0 transition-smooth group-hover:border-primary/60" />
                  <span className="pointer-events-none absolute bottom-2 left-2 h-4 w-4 border-b border-l border-primary/0 transition-smooth group-hover:border-primary/60" />
                  <span className="pointer-events-none absolute bottom-2 right-2 h-4 w-4 border-b border-r border-primary/0 transition-smooth group-hover:border-primary/60" />

                  {uploadLoader.loading ? (
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  ) : (
                    <>
                      <div className="flex h-10 w-10 items-center justify-center border border-border bg-muted transition-smooth group-hover:border-primary/30 group-hover:bg-accent/20">
                        <Upload className="h-5 w-5 text-muted-foreground transition-smooth group-hover:text-primary" />
                      </div>
                      <div className="text-center">
                        <p className="font-mono-tech text-sm font-medium text-muted-foreground tracking-wide transition-smooth group-hover:text-foreground">
                          点击上传真题图片或 PDF
                        </p>
                        <p className="mt-0.5 font-mono-tech text-[10px] text-muted-foreground/50 tracking-widest">
                          PNG / JPG / PDF · MAX 10MB
                        </p>
                      </div>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          {/* Question input */}
          <div className="border border-border bg-card/80 overflow-hidden">
            <div className="flex items-center gap-2 border-b border-border bg-card/60 px-5 py-3">
              <p className="font-mono-tech text-[11px] font-medium text-muted-foreground tracking-widest">
                // INPUT QUESTION TEXT
              </p>
            </div>
            <div className="space-y-3 p-5">
              <Textarea
                value={questionText}
                onChange={(e) => setQuestionText(e.target.value)}
                placeholder={"将真题内容粘贴或输入到这里...\n\n例如: 设有6个结点的无向图，该图至少应有多少条边才能保证是一个连通图？"}
                rows={5}
                className="resize-none font-mono-tech text-sm"
              />
              <Button
                onClick={handleAnalyze}
                disabled={analyzeLoader.loading || !questionText.trim()}
                className="w-full"
              >
                {analyzeLoader.loading
                  ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  : <Send className="mr-2 h-4 w-4" />}
                AI ANALYZE
              </Button>
            </div>
          </div>

          {/* Result */}
          {result && (
            <div className="animate-fade-in-up border border-primary/20 bg-card/80 overflow-hidden">
              {/* Result header */}
              <div className="flex items-center gap-2 border-b border-border bg-card/60 px-5 py-3 scanlines">
                <span className="h-2 w-2 bg-primary animate-glow-pulse" />
                <span className="font-mono-tech text-[11px] font-medium text-primary/80 uppercase tracking-widest">
                  ANALYSIS RESULT //
                </span>
              </div>

              <div className="space-y-4 p-5">
                {/* Knowledge points */}
                {result.knowledge_points.length > 0 && (
                  <div>
                    <div className="mb-2 flex items-center gap-1.5">
                      <Tag className="h-3 w-3 text-muted-foreground" />
                      <p className="font-mono-tech text-[10px] font-medium text-muted-foreground uppercase tracking-widest">
                        KNOWLEDGE POINTS
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {result.knowledge_points.map((kp) => (
                        <Badge key={kp} variant="default" className="font-mono-tech text-[10px]">
                          {kp}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Divider */}
                {result.knowledge_points.length > 0 && (
                  <div className="hr-amber" />
                )}

                {/* Answer */}
                <div className="border-l-2 border-l-primary/30 pl-4">
                  <p className="mb-2 font-mono-tech text-[10px] font-medium text-muted-foreground uppercase tracking-widest">
                    DETAILED ANSWER
                  </p>
                  <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
                    {result.answer}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {analyzeLoader.error && (
            <div className="border border-destructive/30 bg-destructive/5 p-4">
              <p className="font-mono-tech text-xs text-destructive">{analyzeLoader.error}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

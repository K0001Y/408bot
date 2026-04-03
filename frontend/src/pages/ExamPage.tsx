import { useState, useRef } from "react";
import { Upload, Send, Loader2, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SubjectPicker } from "@/components/SubjectPicker";
import { api } from "@/lib/api";
import { useLoading } from "@/hooks/useLoading";

export function ExamPage() {
  const [subject, setSubject] = useState<string | null>(null);
  const [questionText, setQuestionText] = useState("");
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [result, setResult] = useState<{
    answer: string;
    knowledge_points: string[];
  } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const uploadLoader = useLoading();
  const analyzeLoader = useLoading();

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const res = await uploadLoader.run(() => api.uploadExam(file));
    if (res) {
      setUploadedFile(res.filename || file.name);
    }
  };

  const handleAnalyze = async () => {
    if (!questionText.trim()) return;
    const res = await analyzeLoader.run(() =>
      api.analyzeExam({
        question_text: questionText.trim(),
        subject: subject ?? undefined,
      })
    );
    if (res) {
      setResult({ answer: res.answer, knowledge_points: res.knowledge_points });
    }
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-foreground">真题坊</h1>
          <p className="text-xs text-muted-foreground">上传真题图片或输入题目，获取 AI 解析</p>
        </div>
        <SubjectPicker value={subject} onChange={setSubject} showAll={false} />
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {/* Upload area */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Upload className="h-4 w-4 text-primary" />
                上传真题（可选）
              </CardTitle>
            </CardHeader>
            <CardContent>
              <input
                ref={fileRef}
                type="file"
                accept=".png,.jpg,.jpeg,.pdf"
                className="hidden"
                onChange={handleUpload}
              />
              {uploadedFile ? (
                <div className="flex items-center gap-2 rounded-lg border border-border bg-secondary px-3 py-2">
                  <FileText className="h-4 w-4 text-primary" />
                  <span className="flex-1 text-sm text-foreground">{uploadedFile}</span>
                  <button onClick={() => setUploadedFile(null)} className="text-muted-foreground hover:text-foreground">
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => fileRef.current?.click()}
                  disabled={uploadLoader.loading}
                  className="flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border py-8 text-sm text-muted-foreground transition-smooth hover:border-primary/30 hover:text-foreground"
                >
                  {uploadLoader.loading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <>
                      <Upload className="h-5 w-5" />
                      点击上传真题图片或 PDF（支持 PNG/JPG/PDF，最大 10MB）
                    </>
                  )}
                </button>
              )}
            </CardContent>
          </Card>

          {/* Question input */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">输入题目文本</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                value={questionText}
                onChange={(e) => setQuestionText(e.target.value)}
                placeholder="将真题内容粘贴或输入到这里...&#10;&#10;例如: 设有6个结点的无向图，该图至少应有多少条边才能保证是一个连通图？"
                rows={5}
              />
              <Button
                onClick={handleAnalyze}
                disabled={analyzeLoader.loading || !questionText.trim()}
                className="w-full"
              >
                {analyzeLoader.loading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Send className="mr-2 h-4 w-4" />
                )}
                AI 解析
              </Button>
            </CardContent>
          </Card>

          {/* Result */}
          {result && (
            <Card className="animate-fade-in">
              <CardHeader>
                <CardTitle className="text-sm">解析结果</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {result.knowledge_points.length > 0 && (
                  <div>
                    <p className="mb-1.5 text-xs font-medium text-muted-foreground">涉及知识点</p>
                    <div className="flex flex-wrap gap-1.5">
                      {result.knowledge_points.map((kp) => (
                        <Badge key={kp} variant="default">{kp}</Badge>
                      ))}
                    </div>
                  </div>
                )}
                <div>
                  <p className="mb-1.5 text-xs font-medium text-muted-foreground">详细解答</p>
                  <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
                    {result.answer}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {analyzeLoader.error && (
            <Card className="border-destructive/30">
              <CardContent className="p-4 text-sm text-destructive">
                {analyzeLoader.error}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
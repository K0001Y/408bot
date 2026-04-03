import { useState } from "react";
import { Sparkles, BookOpen, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SubjectPicker } from "@/components/SubjectPicker";
import { api, type Exercise } from "@/lib/api";
import { getSubjectName } from "@/lib/constants";
import { useLoading } from "@/hooks/useLoading";
import { cn } from "@/lib/utils";

const QUIZ_TYPES = [
  { key: "choice", label: "选择题" },
  { key: "fill", label: "填空题" },
  { key: "short_answer", label: "简答题" },
  { key: "algorithm", label: "算法题" },
];

const DIFFICULTIES = [
  { key: "easy", label: "简单" },
  { key: "medium", label: "中等" },
  { key: "hard", label: "困难" },
];

export function PracticePage() {
  const [tab, setTab] = useState<"browse" | "generate">("browse");
  const [subject, setSubject] = useState<string | null>(null);
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [answers, setAnswers] = useState<Exercise[]>([]);

  // Generate form
  const [topic, setTopic] = useState("");
  const [quizType, setQuizType] = useState("choice");
  const [difficulty, setDifficulty] = useState("medium");
  const [count, setCount] = useState(3);
  const [generatedQuiz, setGeneratedQuiz] = useState("");

  const browseLoader = useLoading();
  const genLoader = useLoading();

  const fetchExercises = async () => {
    const result = await browseLoader.run(() =>
      api.getExercises({ subject: subject ?? undefined, top_k: 20 })
    );
    if (result) {
      setExercises(result.exercises);
      setAnswers(result.answers);
    }
  };

  const generateQuiz = async () => {
    if (!topic.trim()) return;
    const result = await genLoader.run(() =>
      api.generateQuiz({
        topic: topic.trim(),
        subject: subject ?? undefined,
        quiz_type: quizType,
        count,
        difficulty,
      })
    );
    if (result) {
      setGeneratedQuiz(result.quiz_content);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-foreground">练习室</h1>
          <p className="text-xs text-muted-foreground">浏览教材习题或让 AI 出题</p>
        </div>
        <div className="flex items-center gap-3">
          <SubjectPicker value={subject} onChange={setSubject} />
          <div className="flex rounded-lg border border-border">
            <button
              onClick={() => setTab("browse")}
              className={cn(
                "flex items-center gap-1.5 rounded-l-lg px-3 py-1.5 text-xs font-medium transition-smooth",
                tab === "browse" ? "bg-accent text-accent-foreground" : "text-muted-foreground"
              )}
            >
              <BookOpen className="h-3 w-3" /> 教材习题
            </button>
            <button
              onClick={() => setTab("generate")}
              className={cn(
                "flex items-center gap-1.5 rounded-r-lg px-3 py-1.5 text-xs font-medium transition-smooth",
                tab === "generate" ? "bg-accent text-accent-foreground" : "text-muted-foreground"
              )}
            >
              <Sparkles className="h-3 w-3" /> AI 出题
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {tab === "browse" ? (
          <div className="mx-auto max-w-3xl">
            <div className="mb-4 flex items-center gap-2">
              <Button onClick={fetchExercises} variant="outline" size="sm" disabled={browseLoader.loading}>
                {browseLoader.loading ? <Loader2 className="mr-1.5 h-3 w-3 animate-spin" /> : null}
                加载习题
              </Button>
              {exercises.length > 0 && (
                <span className="text-xs text-muted-foreground">
                  {exercises.length} 道习题 / {answers.length} 条解析
                </span>
              )}
            </div>

            <div className="space-y-3">
              {exercises.map((ex) => (
                <Card key={ex.chunk_id} className="transition-smooth hover:border-primary/30">
                  <CardContent className="p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <Badge variant="default">{getSubjectName(ex.subject_code ?? "")}</Badge>
                      <Badge variant="secondary">{ex.subsection}</Badge>
                      <span className="text-xs text-muted-foreground">{ex.subsection_title}</span>
                    </div>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/80">
                      {ex.preview || ex.content}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl">
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-amber" />
                  AI 智能出题
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">知识点主题</label>
                  <Input
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="如: 二叉树的遍历、页面置换算法、TCP 拥塞控制..."
                  />
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-muted-foreground">题型</label>
                    <div className="flex flex-wrap gap-1">
                      {QUIZ_TYPES.map((t) => (
                        <button
                          key={t.key}
                          onClick={() => setQuizType(t.key)}
                          className={cn(
                            "rounded-md px-2 py-1 text-xs transition-smooth",
                            quizType === t.key ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-secondary"
                          )}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-muted-foreground">难度</label>
                    <div className="flex gap-1">
                      {DIFFICULTIES.map((d) => (
                        <button
                          key={d.key}
                          onClick={() => setDifficulty(d.key)}
                          className={cn(
                            "rounded-md px-2 py-1 text-xs transition-smooth",
                            difficulty === d.key ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-secondary"
                          )}
                        >
                          {d.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-muted-foreground">数量</label>
                    <Input
                      type="number"
                      min={1}
                      max={10}
                      value={count}
                      onChange={(e) => setCount(Number(e.target.value))}
                      className="w-20"
                    />
                  </div>
                </div>

                <Button onClick={generateQuiz} disabled={genLoader.loading || !topic.trim()} className="w-full">
                  {genLoader.loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                  生成题目
                </Button>
              </CardContent>
            </Card>

            {generatedQuiz && (
              <Card className="animate-fade-in">
                <CardHeader>
                  <CardTitle>生成结果</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">{generatedQuiz}</div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
import { useState } from "react";
import { Sparkles, BookOpen, Loader2, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { SubjectPicker } from "@/components/SubjectPicker";
import { api, type Exercise } from "@/lib/api";
import { getSubjectName } from "@/lib/constants";
import { useLoading } from "@/hooks/useLoading";
import { cn } from "@/lib/utils";

const QUIZ_TYPES = [
  { key: "choice",       label: "选择题", mono: "MCQ" },
  { key: "fill",         label: "填空题", mono: "FILL" },
  { key: "short_answer", label: "简答题", mono: "SA" },
  { key: "algorithm",    label: "算法题", mono: "ALGO" },
];

const DIFFICULTIES = [
  { key: "easy",   label: "EASY",   color: "text-emerald-400" },
  { key: "medium", label: "MED",    color: "text-amber-400" },
  { key: "hard",   label: "HARD",   color: "text-red-400" },
];

export function PracticePage() {
  const [tab, setTab] = useState<"browse" | "generate">("browse");
  const [subject, setSubject] = useState<string | null>(null);
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [answers, setAnswers] = useState<Exercise[]>([]);

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
      api.generateQuiz({ topic: topic.trim(), subject: subject ?? undefined, quiz_type: quizType, count, difficulty })
    );
    if (result) setGeneratedQuiz(result.quiz_content);
  };

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <header className="flex flex-shrink-0 items-center justify-between border-b border-border bg-card/50 px-6 py-3">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="font-display text-base font-semibold text-foreground tracking-wide">练习室</h1>
            <p className="font-mono-tech text-[10px] text-muted-foreground tracking-widest">PRACTICE ROOM</p>
          </div>
          {/* Tab toggle — Detroit border-divided style */}
          <div className="flex border border-border">
            <button
              onClick={() => setTab("browse")}
              className={cn(
                "flex items-center gap-1.5 border-r border-border px-3 py-1.5 font-mono-tech text-[10px] font-medium tracking-widest transition-smooth",
                tab === "browse"
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <BookOpen className="h-3 w-3" />
              BROWSE
            </button>
            <button
              onClick={() => setTab("generate")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 font-mono-tech text-[10px] font-medium tracking-widest transition-smooth",
                tab === "generate"
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <Sparkles className="h-3 w-3" />
              AI GEN
            </button>
          </div>
        </div>
        <SubjectPicker value={subject} onChange={setSubject} />
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {tab === "browse" ? (
          <div className="mx-auto max-w-2xl">
            <div className="mb-4 flex items-center gap-3">
              <Button onClick={fetchExercises} variant="outline" size="sm" disabled={browseLoader.loading}>
                {browseLoader.loading
                  ? <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                  : <BookOpen className="mr-1.5 h-3 w-3" />}
                加载习题
              </Button>
              {exercises.length > 0 && (
                <span className="font-mono-tech text-[11px] text-muted-foreground">
                  {exercises.length} 道习题 · {answers.length} 条解析
                </span>
              )}
            </div>

            <div className="space-y-2">
              {exercises.map((ex, idx) => (
                <div
                  key={ex.chunk_id}
                  className="animate-fade-in border border-border bg-card/60 p-4 transition-smooth hover:border-primary/30 border-l-2 border-l-primary/20"
                  style={{ animationDelay: `${idx * 30}ms` }}
                >
                  <div className="mb-2 flex items-center gap-2 flex-wrap">
                    <Badge variant="default" className="font-mono-tech text-[10px]">
                      {getSubjectName(ex.subject_code ?? "")}
                    </Badge>
                    <Badge variant="secondary" className="font-mono-tech text-[10px]">
                      {ex.subsection}
                    </Badge>
                    <span className="font-mono-tech text-[10px] text-muted-foreground">{ex.subsection_title}</span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/80">
                    {ex.preview || ex.content}
                  </p>
                </div>
              ))}

              {exercises.length === 0 && !browseLoader.loading && (
                <div className="flex flex-col items-center justify-center py-16 text-center animate-fade-in-up">
                  <div className="bracket-corners relative mb-4 flex h-14 w-14 items-center justify-center border border-border bg-card">
                    <BookOpen className="h-6 w-6 text-muted-foreground/30" />
                  </div>
                  <p className="font-mono-tech text-[11px] text-muted-foreground tracking-wider">
                    // 点击「加载习题」获取教材练习题
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-2xl space-y-4">
            {/* AI Generate Form */}
            <div className="animate-scale-in border border-border bg-card/80 overflow-hidden">
              {/* Card header */}
              <div className="flex items-center gap-2.5 border-b border-border bg-card/60 px-5 py-3 scanlines">
                <div className="flex h-7 w-7 items-center justify-center gradient-primary">
                  <Zap className="h-3.5 w-3.5 text-primary-foreground" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground tracking-wide">AI 智能出题</p>
                  <p className="font-mono-tech text-[10px] text-muted-foreground tracking-widest">AI QUIZ GENERATOR</p>
                </div>
              </div>

              <div className="space-y-5 p-5">
                {/* Topic */}
                <div>
                  <label className="mb-1.5 block font-mono-tech text-[11px] font-medium text-muted-foreground uppercase tracking-widest">
                    // 知识点主题
                  </label>
                  <Input
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="如: 二叉树的遍历、页面置换算法、TCP 拥塞控制..."
                  />
                </div>

                <div className="grid grid-cols-3 gap-5">
                  {/* Quiz type */}
                  <div>
                    <label className="mb-2 block font-mono-tech text-[10px] font-medium text-muted-foreground uppercase tracking-widest">
                      QUIZ TYPE
                    </label>
                    <div className="flex flex-wrap gap-1">
                      {QUIZ_TYPES.map((t) => (
                        <button
                          key={t.key}
                          onClick={() => setQuizType(t.key)}
                          className={cn(
                            "px-2 py-1 font-mono-tech text-[10px] tracking-widest transition-smooth border",
                            quizType === t.key
                              ? "bg-accent text-accent-foreground border-primary/40"
                              : "text-muted-foreground border-transparent hover:bg-secondary hover:text-foreground hover:border-border"
                          )}
                        >
                          {t.mono}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Difficulty */}
                  <div>
                    <label className="mb-2 block font-mono-tech text-[10px] font-medium text-muted-foreground uppercase tracking-widest">
                      DIFFICULTY
                    </label>
                    <div className="flex gap-1">
                      {DIFFICULTIES.map((d) => (
                        <button
                          key={d.key}
                          onClick={() => setDifficulty(d.key)}
                          className={cn(
                            "px-2 py-1 font-mono-tech text-[10px] tracking-widest transition-smooth border",
                            difficulty === d.key
                              ? "bg-accent text-accent-foreground border-primary/40"
                              : cn("border-transparent hover:bg-secondary", d.color, "hover:border-border")
                          )}
                        >
                          {d.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Count */}
                  <div>
                    <label className="mb-2 block font-mono-tech text-[10px] font-medium text-muted-foreground uppercase tracking-widest">
                      COUNT
                    </label>
                    <Input
                      type="number"
                      min={1}
                      max={10}
                      value={count}
                      onChange={(e) => setCount(Number(e.target.value))}
                      className="w-20 font-mono-tech"
                    />
                  </div>
                </div>

                <Button
                  onClick={generateQuiz}
                  disabled={genLoader.loading || !topic.trim()}
                  className="w-full"
                >
                  {genLoader.loading
                    ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    : <Sparkles className="mr-2 h-4 w-4" />}
                  GENERATE
                </Button>
              </div>
            </div>

            {/* Generated result */}
            {generatedQuiz && (
              <div className="animate-fade-in-up border border-primary/20 bg-card/80 overflow-hidden">
                <div className="flex items-center gap-2 border-b border-border px-5 py-3 bg-card/60">
                  <span className="h-2 w-2 bg-primary animate-glow-pulse" />
                  <span className="font-mono-tech text-[11px] font-medium text-primary/80 uppercase tracking-widest">
                    OUTPUT //
                  </span>
                </div>
                <div className="p-5 border-l-2 border-l-primary/30">
                  <div className="whitespace-pre-wrap font-mono-tech text-sm leading-relaxed text-foreground/90">
                    {generatedQuiz}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

import { cn } from "@/lib/utils";
import {
  BookOpen,
  GitFork,
  Dumbbell,
  FileText,
  BookMarked,
  type LucideIcon,
} from "lucide-react";

export type PageId = "knowledge" | "graph" | "practice" | "exam" | "mistakes";

interface NavItem {
  id: PageId;
  label: string;
  sublabel: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { id: "knowledge", label: "知识库", sublabel: "KNOWLEDGE", icon: BookOpen },
  { id: "graph",     label: "图谱",   sublabel: "GRAPH",     icon: GitFork },
  { id: "practice",  label: "练习室", sublabel: "PRACTICE",  icon: Dumbbell },
  { id: "exam",      label: "真题坊", sublabel: "EXAM",      icon: FileText },
  { id: "mistakes",  label: "错题本", sublabel: "MISTAKES",  icon: BookMarked },
];

interface SidebarProps {
  active: PageId;
  onChange: (id: PageId) => void;
}

export function Sidebar({ active, onChange }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-[200px] flex-col border-r border-border bg-card">
      {/* Amber top accent line */}
      <div className="h-[2px] w-full gradient-primary flex-shrink-0" />

      {/* Logo area */}
      <div className="flex items-center gap-3 border-b border-border px-4 py-4 flex-shrink-0">
        {/* Square logo — no rounding */}
        <div className="relative flex h-9 w-9 shrink-0 items-center justify-center bg-primary shadow-glow">
          <span className="font-display text-sm font-bold text-primary-foreground tracking-widest">408</span>
        </div>
        <div className="min-w-0">
          <p className="font-display text-sm font-semibold text-foreground leading-tight truncate tracking-wider">
            408 BOT
          </p>
          <p className="font-mono-tech text-[10px] text-muted-foreground truncate tracking-widest">
            CYBERLIFE OS
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col gap-px overflow-y-auto p-2">
        {NAV_ITEMS.map((item) => {
          const isActive = active === item.id;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => onChange(item.id)}
              className={cn(
                "group relative flex w-full items-center gap-3 px-3 py-2.5 text-left transition-smooth",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              {/* Active left amber bar */}
              {isActive && (
                <span className="absolute left-0 top-0 h-full w-[2px] gradient-primary" />
              )}

              <Icon
                className={cn(
                  "h-[16px] w-[16px] shrink-0 transition-fast",
                  isActive ? "text-accent-foreground" : "text-muted-foreground group-hover:text-foreground"
                )}
              />

              <div className="min-w-0 flex-1">
                <p className="font-display text-sm font-medium leading-none tracking-wide">
                  {item.label}
                </p>
                <p className="mt-0.5 font-mono-tech text-[9px] opacity-35 leading-none tracking-widest">
                  {item.sublabel}
                </p>
              </div>

              {/* Active right edge tick */}
              {isActive && (
                <span className="text-[8px] font-mono-tech text-accent-foreground/60">▶</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom status bar */}
      <div className="flex-shrink-0 border-t border-border px-4 py-3">
        <div className="flex items-center justify-between">
          <span className="font-mono-tech text-[10px] text-muted-foreground/40 tracking-widest">V0.1.0</span>
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 bg-primary animate-glow-pulse" />
            <span className="font-mono-tech text-[9px] text-muted-foreground/35 tracking-widest">ONLINE</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

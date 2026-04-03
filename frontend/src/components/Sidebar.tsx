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
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { id: "knowledge", label: "知识库", icon: BookOpen },
  { id: "graph", label: "图谱", icon: GitFork },
  { id: "practice", label: "练习室", icon: Dumbbell },
  { id: "exam", label: "真题坊", icon: FileText },
  { id: "mistakes", label: "错题本", icon: BookMarked },
];

interface SidebarProps {
  active: PageId;
  onChange: (id: PageId) => void;
}

export function Sidebar({ active, onChange }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-[68px] flex-col items-center border-r border-border bg-card py-4">
      {/* Logo */}
      <div className="mb-6 flex h-10 w-10 items-center justify-center rounded-lg gradient-primary shadow-glow">
        <span className="text-sm font-bold text-primary-foreground">408</span>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col items-center gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive = active === item.id;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => onChange(item.id)}
              className={cn(
                "group relative flex h-11 w-11 items-center justify-center rounded-lg transition-smooth",
                isActive
                  ? "bg-accent text-accent-foreground shadow-glow"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
              title={item.label}
            >
              <Icon className="h-[18px] w-[18px]" />

              {/* Active indicator */}
              {isActive && (
                <span className="absolute -left-[1px] top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full gradient-primary" />
              )}

              {/* Tooltip */}
              <span className="pointer-events-none absolute left-full ml-3 whitespace-nowrap rounded-md bg-popover px-2.5 py-1 text-xs font-medium text-popover-foreground opacity-0 shadow-md transition-smooth group-hover:opacity-100">
                {item.label}
              </span>
            </button>
          );
        })}
      </nav>

      {/* Bottom version */}
      <div className="text-[10px] text-muted-foreground">v0.1</div>
    </aside>
  );
}
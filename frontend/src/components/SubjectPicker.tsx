import { cn } from "@/lib/utils";
import { SUBJECTS } from "@/lib/constants";

interface SubjectPickerProps {
  value: string | null;
  onChange: (code: string | null) => void;
  showAll?: boolean;
}

export function SubjectPicker({ value, onChange, showAll = true }: SubjectPickerProps) {
  return (
    <div className="flex items-center gap-1.5">
      {showAll && (
        <button
          onClick={() => onChange(null)}
          className={cn(
            "rounded-md px-2.5 py-1 text-xs font-medium transition-smooth",
            value === null
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:bg-secondary hover:text-foreground"
          )}
        >
          全部
        </button>
      )}
      {SUBJECTS.map((s) => (
        <button
          key={s.code}
          onClick={() => onChange(s.code)}
          className={cn(
            "rounded-md px-2.5 py-1 text-xs font-medium transition-smooth",
            value === s.code
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:bg-secondary hover:text-foreground"
          )}
        >
          {s.short}
        </button>
      ))}
    </div>
  );
}
import { cn } from "@/lib/utils";
import { SUBJECTS } from "@/lib/constants";

interface SubjectPickerProps {
  value: string | null;
  onChange: (code: string | null) => void;
  showAll?: boolean;
}

export function SubjectPicker({ value, onChange, showAll = true }: SubjectPickerProps) {
  return (
    <div className="flex items-center gap-1">
      {showAll && (
        <button
          onClick={() => onChange(null)}
          className={cn(
            "rounded-none px-2.5 py-1 font-mono-tech text-[10px] font-medium tracking-widest transition-smooth",
            value === null
              ? "bg-accent text-accent-foreground border border-primary/30 shadow-teal-sm"
              : "text-muted-foreground hover:bg-secondary hover:text-foreground border border-transparent"
          )}
        >
          ALL
        </button>
      )}
      {SUBJECTS.map((s) => (
        <button
          key={s.code}
          onClick={() => onChange(s.code)}
          className={cn(
            "rounded-none px-2.5 py-1 font-mono-tech text-[10px] font-medium tracking-widest transition-smooth",
            value === s.code
              ? "bg-accent text-accent-foreground border border-primary/30 shadow-teal-sm"
              : "text-muted-foreground hover:bg-secondary hover:text-foreground border border-transparent"
          )}
        >
          {s.short}
        </button>
      ))}
    </div>
  );
}

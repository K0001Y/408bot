import { useState, useCallback, useEffect, createContext, useContext } from "react";
import { X, AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ───

export type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (type: ToastType, message: string, duration?: number) => void;
  removeToast: (id: string) => void;
}

// ─── Context ───

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

// ─── Provider ───

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((type: ToastType, message: string, duration = 3000) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    setToasts((prev) => [...prev.slice(-4), { id, type, message, duration }]);

    if (duration > 0) {
      setTimeout(() => removeToast(id), duration);
    }
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

// ─── Toast Container (renders in portal position) ───

function ToastContainer({ toasts, onRemove }: { toasts: Toast[]; onRemove: (id: string) => void }) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed right-4 top-4 z-[9999] flex flex-col gap-2" style={{ maxWidth: 400 }}>
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  );
}

// ─── Single Toast Item ───

const TOAST_STYLES: Record<ToastType, { border: string; icon: string; bg: string }> = {
  error: {
    border: "border-red-500/60",
    icon: "text-red-400",
    bg: "bg-red-500/5",
  },
  warning: {
    border: "border-primary/60",
    icon: "text-primary",
    bg: "bg-primary/5",
  },
  success: {
    border: "border-emerald-500/60",
    icon: "text-emerald-400",
    bg: "bg-emerald-500/5",
  },
  info: {
    border: "border-muted-foreground/40",
    icon: "text-muted-foreground",
    bg: "bg-muted/10",
  },
};

const TOAST_ICONS: Record<ToastType, React.ComponentType<{ className?: string }>> = {
  error: AlertTriangle,
  warning: AlertTriangle,
  success: CheckCircle2,
  info: Info,
};

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: (id: string) => void }) {
  const [visible, setVisible] = useState(false);
  const style = TOAST_STYLES[toast.type];
  const Icon = TOAST_ICONS[toast.type];

  useEffect(() => {
    // Trigger enter animation
    requestAnimationFrame(() => setVisible(true));
  }, []);

  const handleClose = () => {
    setVisible(false);
    setTimeout(() => onRemove(toast.id), 150);
  };

  return (
    <div
      className={cn(
        "flex items-start gap-2.5 border bg-card/95 px-4 py-3 backdrop-blur-md transition-all duration-150",
        style.border,
        style.bg,
        visible ? "translate-x-0 opacity-100" : "translate-x-4 opacity-0",
      )}
    >
      {/* Left accent line */}
      <div className={cn("mt-0.5 h-4 w-[2px]", style.icon.replace("text-", "bg-"))} />

      {/* Icon */}
      <Icon className={cn("mt-0.5 h-3.5 w-3.5 shrink-0", style.icon)} />

      {/* Message */}
      <p className="flex-1 font-mono-tech text-[11px] leading-relaxed text-foreground/90 tracking-wide">
        {toast.message}
      </p>

      {/* Close button */}
      <button
        onClick={handleClose}
        className="shrink-0 p-0.5 text-muted-foreground/50 transition-smooth hover:text-foreground"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

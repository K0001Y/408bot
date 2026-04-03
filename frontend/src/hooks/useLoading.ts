import { useState, useCallback } from "react";
import { useToast } from "@/components/ui/toast";

export function useLoading() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  let toast: ReturnType<typeof useToast> | null = null;
  try {
    toast = useToast();
  } catch {
    // ToastProvider 未挂载时静默降级
  }

  const run = useCallback(async <T>(fn: () => Promise<T>): Promise<T | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await fn();
      return result;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "未知错误";
      setError(msg);
      toast?.addToast("error", msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, [toast]);

  return { loading, error, run, setError };
}

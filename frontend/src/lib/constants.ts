export const SUBJECTS = [
  { code: "ds", name: "数据结构", short: "DS" },
  { code: "os", name: "操作系统", short: "OS" },
  { code: "co", name: "计算机组成原理", short: "CO" },
  { code: "cn", name: "计算机网络", short: "CN" },
] as const;

export type SubjectCode = (typeof SUBJECTS)[number]["code"];

export function getSubjectName(code: string): string {
  return SUBJECTS.find((s) => s.code === code)?.name ?? code;
}

export function getSubjectShort(code: string): string {
  return SUBJECTS.find((s) => s.code === code)?.short ?? code.toUpperCase();
}
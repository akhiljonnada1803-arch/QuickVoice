import { FileText, FileSpreadsheet, Globe } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { KbSourceType, KbStatus } from "@/src/lib/api/types";

export interface SourceMeta { Icon: LucideIcon; iconCls: string }

export const SOURCE_META: Record<KbSourceType, SourceMeta> = {
  PDF:  { Icon: FileText,        iconCls: "border-red-500/20 bg-red-500/10 text-red-400" },
  DOCX: { Icon: FileText,        iconCls: "border-blue-500/20 bg-blue-500/10 text-blue-400" },
  TXT:  { Icon: FileText,        iconCls: "border-slate-500/20 bg-slate-500/10 text-slate-400" },
  CSV:  { Icon: FileSpreadsheet, iconCls: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400" },
  XLSX: { Icon: FileSpreadsheet, iconCls: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400" },
  XLS:  { Icon: FileSpreadsheet, iconCls: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400" },
  URL:  { Icon: Globe,           iconCls: "border-violet-500/20 bg-violet-500/10 text-violet-400" },
};

export const FALLBACK_META: SourceMeta = {
  Icon: FileText,
  iconCls: "border-muted bg-muted/30 text-muted-foreground",
};

export function StatusChip({ status }: { status: KbStatus }) {
  if (status === "ACTIVE") {
    return (
      <span className="inline-flex items-center rounded-sm border border-emerald-500/30 bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-400">
        Active
      </span>
    );
  }
  if (status === "ERROR") {
    return (
      <span className="inline-flex items-center rounded-sm border border-red-500/30 bg-red-500/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-red-400">
        Error
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-sm border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-400">
      <span className="size-1.5 animate-pulse rounded-full bg-amber-400" />
      Processing
    </span>
  );
}

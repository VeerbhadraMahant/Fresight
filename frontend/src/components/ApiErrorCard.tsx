import { AlertOctagon } from "lucide-react";

export function ApiErrorCard({
  title = "Couldn’t reach the API",
  message,
  note,
  onRetry,
}: {
  title?: string;
  message: string;
  note?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="border border-graphite bg-canvas p-8 md:p-10" style={{ borderRadius: "6px 0 0 0" }}>
      <div className="flex items-start gap-4">
        <AlertOctagon size={22} strokeWidth={1.5} className="mt-1 shrink-0 text-ember" />
        <div className="min-w-0">
          <h2 className="h-section">{title}</h2>
          <p className="caption mt-2 break-words">{message}</p>
          {note && <p className="meta mt-3 max-w-xl">{note}</p>}
          {onRetry && (
            <button type="button" className="btn-primary mt-6" onClick={onRetry}>
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

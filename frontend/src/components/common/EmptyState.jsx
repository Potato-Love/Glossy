import { Inbox } from "lucide-react";

export default function EmptyState({ title = "표시할 항목이 없습니다", description }) {
  return (
    <div className="empty-state">
      <div>
        <Inbox size={36} strokeWidth={1.5} />
        <strong>{title}</strong>
        {description && <span>{description}</span>}
      </div>
    </div>
  );
}

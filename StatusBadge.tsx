type BadgeVariant = "reviewed" | "needs_review" | "processing" | "uploaded";

const VARIANT_STYLES: Record<BadgeVariant, string> = {
  reviewed: "bg-green-100 text-green-700",
  needs_review: "bg-amber-100 text-amber-700",
  processing: "bg-blue-100 text-blue-700",
  uploaded: "bg-slate-100 text-slate-600",
};

const VARIANT_LABELS: Record<BadgeVariant, string> = {
  reviewed: "Reviewed",
  needs_review: "Needs review",
  processing: "Processing",
  uploaded: "Uploaded",
};

interface Props {
  variant: BadgeVariant;
}

/** Reusable pill badge — matches Arwa's status-badge pattern (e.g. the
 * green "Open" pill on the accounting period). Kept as a single small
 * component since status badges show up throughout the review flow and
 * would otherwise get re-implemented slightly differently each time. */
export default function StatusBadge({ variant }: Props) {
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${VARIANT_STYLES[variant]}`}>
      {VARIANT_LABELS[variant]}
    </span>
  );
}

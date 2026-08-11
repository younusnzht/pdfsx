import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { listTransactions } from "../api/statements";
import TransactionRow from "../components/TransactionRow";

/**
 * The core screen: extracted rows next to (eventually) the source PDF, so a
 * reviewer can confirm or correct anything flagged uncertain. This human
 * verification step is what gets the product to "100% correct" — the
 * extraction pipeline alone won't, on scanned/unfamiliar statements. See
 * docs/architecture.md for the reasoning.
 */
export default function ReviewPage() {
  const { statementId } = useParams<{ statementId: string }>();

  const { data: transactions, isLoading } = useQuery({
    queryKey: ["transactions", statementId],
    queryFn: () => listTransactions(statementId!),
    enabled: !!statementId,
  });

  if (isLoading) return <div className="p-8">Loading...</div>;

  const uncertainCount = transactions?.filter((t) => t.is_uncertain).length ?? 0;

  return (
    <div className="mx-auto max-w-5xl py-8">
      <h1 className="mb-2 text-2xl font-semibold">Review extracted transactions</h1>
      {uncertainCount > 0 && (
        <p className="mb-4 text-sm text-amber-600">
          {uncertainCount} row{uncertainCount === 1 ? "" : "s"} need review — highlighted below.
        </p>
      )}
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="py-2 pr-4">Date</th>
            <th className="py-2 pr-4">Description</th>
            <th className="py-2 pr-4 text-right">Debit</th>
            <th className="py-2 pr-4 text-right">Credit</th>
            <th className="py-2 pr-4"></th>
          </tr>
        </thead>
        <tbody>
          {transactions?.map((transaction) => (
            <TransactionRow key={transaction.id} transaction={transaction} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

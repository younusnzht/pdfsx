import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import TransactionRow from "../components/TransactionRow";
import { listTransactions } from "../api/statements";

export default function ReviewPage() {
  const { statementId } = useParams<{ statementId: string }>();

  const { data: transactions, isLoading } = useQuery({
    queryKey: ["transactions", statementId],
    queryFn: () => listTransactions(statementId!),
    enabled: !!statementId,
  });

  const uncertainCount = transactions?.filter((t) => t.is_uncertain).length ?? 0;

  return (
    <AppLayout title="Bank Statements">
      <div className="mb-5">
        <div className="text-2xl font-extrabold text-slate-900">Review extracted transactions</div>
        <div className="text-slate-500 text-sm mt-0.5">
          {uncertainCount > 0
            ? `${uncertainCount} row${uncertainCount === 1 ? "" : "s"} need review — highlighted below.`
            : "Confirm each row before it's finalized."}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-6 text-sm text-slate-500">Loading...</div>
        ) : (
          <table className="w-full border-collapse text-[12.5px]">
            <thead>
              <tr className="bg-slate-50 text-slate-500 text-left">
                <th className="py-2.5 px-5 font-semibold">Date</th>
                <th className="py-2.5 px-2 font-semibold">Description</th>
                <th className="py-2.5 px-2 font-semibold text-right">Debit</th>
                <th className="py-2.5 px-2 font-semibold text-right">Credit</th>
                <th className="py-2.5 px-5 font-semibold text-right">Status</th>
              </tr>
            </thead>
            <tbody>
              {transactions?.map((transaction) => (
                <TransactionRow key={transaction.id} transaction={transaction} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AppLayout>
  );
}

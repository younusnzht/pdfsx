import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { correctTransaction, type Transaction } from "../api/statements";
import StatusBadge from "./StatusBadge";

interface Props {
  transaction: Transaction;
}

/**
 * Every field is editable inline. Saving a change that differs from the
 * original raw value marks the row as corrected server-side, which is what
 * feeds the ml_training_samples table — see backend/app/models/ml_training_sample.py.
 */
export default function TransactionRow({ transaction }: Props) {
  const [values, setValues] = useState(transaction);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => correctTransaction(transaction.id, values),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["transactions"] }),
  });

  const rowClass = transaction.is_uncertain && !transaction.reviewed ? "bg-amber-50" : "";
  const badgeVariant = transaction.reviewed ? "reviewed" : transaction.is_uncertain ? "needs_review" : "uploaded";

  return (
    <tr className={`border-t border-slate-100 ${rowClass}`}>
      <td className="py-2.5 px-5 text-slate-700">
        <input
          className="w-24 bg-transparent"
          value={values.raw_date}
          onChange={(e) => setValues({ ...values, raw_date: e.target.value })}
        />
      </td>
      <td className="py-2.5 px-2 text-slate-700">
        <input
          className="w-full bg-transparent"
          value={values.raw_description}
          onChange={(e) => setValues({ ...values, raw_description: e.target.value })}
        />
      </td>
      <td className="py-2.5 px-2 text-right">
        <input
          className="w-24 bg-transparent text-right text-red-600 font-semibold"
          value={values.raw_debit ?? ""}
          onChange={(e) => setValues({ ...values, raw_debit: e.target.value || null })}
        />
      </td>
      <td className="py-2.5 px-2 text-right">
        <input
          className="w-24 bg-transparent text-right text-green-600 font-semibold"
          value={values.raw_credit ?? ""}
          onChange={(e) => setValues({ ...values, raw_credit: e.target.value || null })}
        />
      </td>
      <td className="py-2.5 px-5 text-right">
        {transaction.reviewed ? (
          <StatusBadge variant="reviewed" />
        ) : (
          <button
            className="text-xs text-blue-600 font-medium disabled:text-slate-300"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
          >
            confirm
          </button>
        )}
        {!transaction.reviewed && transaction.is_uncertain && <div className="mt-1"><StatusBadge variant="needs_review" /></div>}
      </td>
    </tr>
  );
}

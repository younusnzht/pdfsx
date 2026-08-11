import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { correctTransaction, type Transaction } from "../api/statements";

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

  return (
    <tr className={`border-b ${rowClass}`}>
      <td className="py-2 pr-4">
        <input
          className="w-24 bg-transparent"
          value={values.raw_date}
          onChange={(e) => setValues({ ...values, raw_date: e.target.value })}
        />
      </td>
      <td className="py-2 pr-4">
        <input
          className="w-full bg-transparent"
          value={values.raw_description}
          onChange={(e) => setValues({ ...values, raw_description: e.target.value })}
        />
      </td>
      <td className="py-2 pr-4 text-right">
        <input
          className="w-24 bg-transparent text-right"
          value={values.raw_debit ?? ""}
          onChange={(e) => setValues({ ...values, raw_debit: e.target.value || null })}
        />
      </td>
      <td className="py-2 pr-4 text-right">
        <input
          className="w-24 bg-transparent text-right"
          value={values.raw_credit ?? ""}
          onChange={(e) => setValues({ ...values, raw_credit: e.target.value || null })}
        />
      </td>
      <td className="py-2 pr-4">
        <button
          className="text-xs text-blue-600 disabled:text-gray-300"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
        >
          {transaction.reviewed ? "✓ reviewed" : "confirm"}
        </button>
      </td>
    </tr>
  );
}

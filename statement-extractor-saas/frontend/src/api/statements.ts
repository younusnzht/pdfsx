import { apiClient } from "./client";

export interface Transaction {
  id: string;
  raw_date: string;
  raw_description: string;
  raw_debit: string | null;
  raw_credit: string | null;
  confidence: number;
  is_uncertain: boolean;
  reviewed: boolean;
  row_order: number;
}

export async function uploadStatement(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post("/statements/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data as { statement_id: string; filename: string; status: string };
}

export async function getStatement(statementId: string) {
  const { data } = await apiClient.get(`/statements/${statementId}`);
  return data;
}

export async function listTransactions(statementId: string) {
  const { data } = await apiClient.get(`/transactions/by-statement/${statementId}`);
  return data.transactions as Transaction[];
}

export async function correctTransaction(transactionId: string, correction: Partial<Transaction>) {
  const { data } = await apiClient.patch(`/transactions/${transactionId}`, correction);
  return data;
}

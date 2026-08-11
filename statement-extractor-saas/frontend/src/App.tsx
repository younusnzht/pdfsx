import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import ReviewPage from "./pages/ReviewPage";
import UploadPage from "./pages/UploadPage";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/statements/:statementId" element={<ReviewPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

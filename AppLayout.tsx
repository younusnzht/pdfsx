import type { ReactNode } from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

interface Props {
  title: string;
  children: ReactNode;
}

/** Wraps every page in the Sidebar + Topbar shell, matching Arwa 1.0's
 * layout. Once this module is embedded inside Arwa 1.0 itself, this
 * wrapper is what gets dropped (Arwa supplies its own shell) — the pages
 * underneath don't need to change. */
export default function AppLayout({ title, children }: Props) {
  return (
    <div className="flex h-screen font-sans">
      <Sidebar />
      <div className="flex-1 bg-slate-50 flex flex-col overflow-y-auto">
        <Topbar title={title} />
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

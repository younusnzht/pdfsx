import { NavLink } from "react-router-dom";

/**
 * Styled to match Arwa 1.0's sidebar so this module drops into the
 * Accounting section later with no visual seam. Nav items below are
 * placeholders for pdfsx's own routes today (Bank Statements is the only
 * one that's real) — once embedded in Arwa, this component gets replaced
 * by Arwa's own sidebar entirely; pdfsx's screens just need to look right
 * inside it.
 */
export default function Sidebar() {
  const navItemClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm mb-0.5 transition-colors ${
      isActive
        ? "bg-blue-500/15 border-l-2 border-blue-500 text-blue-50 font-semibold pl-2"
        : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
    }`;

  return (
    <div className="w-60 bg-slate-950 flex flex-col flex-shrink-0 h-screen">
      <div className="px-4.5 py-5 flex items-center gap-2.5 border-b border-slate-800">
        <div className="w-8.5 h-8.5 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center font-bold text-white text-sm">
          P
        </div>
        <div>
          <div className="text-white font-bold text-[15px] leading-tight">pdfsx</div>
          <div className="text-slate-500 text-[9px] tracking-wider">STATEMENT EXTRACTOR</div>
        </div>
      </div>

      <div className="px-3 py-4 flex-1">
        <div className="text-slate-600 text-[10px] font-bold tracking-wider px-2 mb-1.5">ACCOUNTING</div>
        <NavLink to="/" className={navItemClass}>
          <span>🏦</span> Bank Statements
        </NavLink>
      </div>

      <div className="p-3 border-t border-slate-800 flex items-center gap-2.5">
        <div className="w-7.5 h-7.5 rounded-full bg-purple-600 flex items-center justify-center text-white text-xs font-semibold">
          Y
        </div>
        <div>
          <div className="text-slate-200 text-xs font-semibold">Younus Azhar</div>
          <div className="text-slate-500 text-[10px]">AITC Inc.</div>
        </div>
      </div>
    </div>
  );
}

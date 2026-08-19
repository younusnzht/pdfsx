interface Props {
  title: string;
}

export default function Topbar({ title }: Props) {
  return (
    <div className="bg-white border-b border-slate-200 px-6 py-3.5 flex items-center gap-4">
      <div className="text-lg font-bold text-slate-900">{title}</div>
      <div className="flex-1 max-w-sm bg-slate-100 rounded-lg px-3.5 py-2 text-slate-400 text-sm ml-5">
        🔍 Search statements, institutions...
      </div>
      <div className="ml-auto flex items-center gap-3.5">
        <span className="text-base">🔔</span>
        <div className="w-7.5 h-7.5 rounded-full bg-purple-600 flex items-center justify-center text-white text-xs font-semibold">
          Y
        </div>
      </div>
    </div>
  );
}

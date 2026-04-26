import { NavLink, Outlet } from 'react-router-dom';
import { BookOpen, FileText, MessageSquare, Search } from 'lucide-react';

const navItems = [
  { to: '/', icon: BookOpen, label: '概览' },
  { to: '/documents', icon: FileText, label: '文献管理' },
  { to: '/search', icon: Search, label: '知识检索' },
  { to: '/chat', icon: MessageSquare, label: '学术对话' },
];

export default function Layout() {
  return (
    <div className="min-h-screen text-primary">
      <div className="mx-auto flex min-h-screen w-full max-w-[1480px] flex-col gap-4 px-3 py-3 md:flex-row md:px-5 md:py-5">
        <aside className="paper-panel w-full min-w-0 overflow-hidden rounded-2xl md:sticky md:top-5 md:flex md:h-[calc(100vh-2.5rem)] md:w-72 md:flex-col">
          <div className="flex items-center gap-3 px-5 py-5">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary">
              <BookOpen className="h-6 w-6 text-accent" />
            </div>
            <div className="min-w-0">
              <h1 className="font-heading text-2xl font-semibold leading-none tracking-normal text-primary">
                Paper Agent
              </h1>
              <p className="mt-1 text-xs font-medium tracking-[0.18em] text-muted">RESEARCH COPILOT</p>
            </div>
          </div>

          <div className="mx-5 hidden h-px bg-primary/10 md:block" />

          <nav className="grid max-w-full grid-cols-2 gap-2 px-4 pb-4 md:block md:space-y-1 md:px-4 md:py-5">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `group flex min-h-11 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-default ${
                    isActive
                      ? 'bg-primary text-white shadow-sm'
                      : 'text-secondary hover:bg-white hover:text-primary'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={`flex h-8 w-8 items-center justify-center rounded-lg transition-default ${
                        isActive ? 'bg-white/10 text-accent' : 'bg-primary/5 text-secondary group-hover:bg-accent/15 group-hover:text-primary'
                      }`}
                    >
                      <item.icon className="h-4.5 w-4.5" />
                    </span>
                    <span>{item.label}</span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto hidden px-5 pb-5 md:block">
            <div className="rounded-2xl border border-primary/10 bg-white/65 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Workspace</p>
              <p className="mt-2 text-sm leading-6 text-secondary">
                上传、索引、检索与对话集中在一个轻量工作台里。
              </p>
            </div>
          </div>
        </aside>

        <main className="w-full min-w-0 flex-1">
          <div className="mx-auto w-full max-w-6xl pb-8 md:pt-1">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

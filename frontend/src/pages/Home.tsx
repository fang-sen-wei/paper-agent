import { useEffect, useState } from 'react';
import { Activity, ArrowRight, FileText, MessageSquare, Search } from 'lucide-react';
import { getHealth, listChatSessions, listDocuments } from '../api/client';

export default function Home() {
  const [health, setHealth] = useState<{ status: string; version: string; name: string } | null>(null);
  const [docCount, setDocCount] = useState(0);
  const [chatCount, setChatCount] = useState(0);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
    listDocuments().then((docs) => setDocCount(docs.length)).catch(() => {});
    listChatSessions().then((sessions) => setChatCount(sessions.length)).catch(() => {});
  }, []);

  const cards = [
    { label: '文献数量', value: docCount, icon: FileText, href: '#/documents', tone: 'bg-cyan-50 text-cyan-700' },
    { label: '会话数量', value: chatCount, icon: MessageSquare, href: '#/chat', tone: 'bg-emerald-50 text-emerald-700' },
    {
      label: '服务状态',
      value: health?.status === 'ok' ? '正常' : '异常',
      icon: Activity,
      href: '#',
      tone: health?.status === 'ok' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700',
    },
  ];

  return (
    <div className="space-y-5 md:space-y-6">
      <section className="paper-panel min-w-0 overflow-hidden rounded-3xl">
        <div className="grid min-w-0 gap-8 p-6 md:grid-cols-[minmax(0,1fr)_280px] md:p-10">
          <div className="flex min-w-0 flex-col justify-center">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent">Academic Knowledge Base</p>
            <h1 className="mt-4 max-w-3xl break-words text-balance font-heading text-4xl font-semibold leading-tight text-primary md:text-6xl">
              让文献整理、检索和问答变得清爽。
            </h1>
            <p className="mt-5 max-w-2xl break-words text-base leading-8 text-secondary md:text-lg">
              Paper Agent 帮您把学术资料沉淀为个人知识库，在需要时快速找到证据，并基于原文进行可追溯的 AI 对话。
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <a
                href="#/documents"
                className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white transition-default hover:bg-secondary"
              >
                上传文献
                <ArrowRight className="h-4 w-4" />
              </a>
              <a
                href="#/search"
                className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-primary/15 bg-white/70 px-5 py-2.5 text-sm font-semibold text-primary transition-default hover:border-accent hover:bg-white"
              >
                <Search className="h-4 w-4" />
                知识检索
              </a>
            </div>
          </div>

          <div className="min-w-0 rounded-2xl border border-primary/10 bg-primary p-5 text-white">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Today</span>
              <span className="rounded-full bg-accent/20 px-2.5 py-1 text-xs font-semibold text-accent">
                {health?.status === 'ok' ? 'ONLINE' : 'CHECK'}
              </span>
            </div>
            <div className="mt-10 space-y-5">
              <div>
                <p className="text-5xl font-semibold leading-none">{docCount}</p>
                <p className="mt-2 text-sm text-white/60">已纳入文献</p>
              </div>
              <div className="h-px bg-white/10" />
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-2xl font-semibold">{chatCount}</p>
                  <p className="mt-1 text-xs text-white/55">对话会话</p>
                </div>
                <div>
                  <p className="text-2xl font-semibold">{health?.version || '-'}</p>
                  <p className="mt-1 text-xs text-white/55">版本</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {cards.map((card) => (
          <a
            key={card.label}
            href={card.href}
            className="soft-panel group rounded-2xl p-5 transition-default hover:border-accent/60 hover:bg-white"
          >
            <div className="flex items-center justify-between gap-4">
              <span className={`flex h-11 w-11 items-center justify-center rounded-xl ${card.tone}`}>
                <card.icon className="h-5 w-5" />
              </span>
              {card.href !== '#' && <ArrowRight className="h-4 w-4 text-muted transition-default group-hover:text-primary" />}
            </div>
            <div className="mt-5 font-heading text-3xl font-semibold text-primary">{card.value}</div>
            <div className="mt-1 text-sm text-muted">{card.label}</div>
          </a>
        ))}
      </section>

      <section className="paper-panel rounded-3xl p-6 md:p-8">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent">Workflow</p>
            <h2 className="mt-2 font-heading text-3xl font-semibold text-primary">快速开始</h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-muted">
            三步把零散论文变成可检索、可引用、可对话的研究资产。
          </p>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {[
            { step: '01', title: '上传文献', desc: '支持 PDF、Word、TXT 等格式，批量上传您的研究资料。', href: '#/documents' },
            { step: '02', title: '解析索引', desc: '系统自动解析文档内容，构建可检索的向量知识库。', href: '#/documents' },
            { step: '03', title: '智能对话', desc: '基于文献内容进行问答，获得带引用来源的专业回答。', href: '#/chat' },
          ].map((item) => (
            <a
              key={item.step}
              href={item.href}
              className="group rounded-2xl border border-primary/10 bg-white/65 p-5 transition-default hover:border-accent/60 hover:bg-white"
            >
              <div className="font-heading text-3xl font-semibold text-accent">{item.step}</div>
              <h3 className="mt-4 text-base font-semibold text-primary transition-default group-hover:text-accent">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{item.desc}</p>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}

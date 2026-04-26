import { useState } from 'react';
import { Search as SearchIcon, Quote } from 'lucide-react';
import { getErrorMessage, searchDocuments, type SearchResponse } from '../api/client';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await searchDocuments(query.trim(), 5);
      setResult(res);
    } catch (err: unknown) {
      setError(getErrorMessage(err, '检索失败'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5 md:space-y-6">
      <section className="paper-panel rounded-3xl p-6 md:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent">Semantic Search</p>
        <h1 className="mt-2 font-heading text-4xl font-semibold text-primary">知识检索</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">在您的文献知识库中搜索相关内容，快速定位原文证据。</p>

        <form onSubmit={handleSearch} className="mt-6">
          <div className="flex flex-col gap-3 rounded-2xl border border-primary/10 bg-white/70 p-2 sm:flex-row">
            <div className="relative min-w-0 flex-1">
              <SearchIcon className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="输入您的问题，例如：这篇论文的主要结论是什么？"
                className="min-h-12 w-full rounded-xl border border-transparent bg-transparent pl-12 pr-4 text-sm text-primary outline-none transition-default placeholder:text-muted focus:border-accent/40 focus:bg-white"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
              className="inline-flex min-h-12 items-center justify-center rounded-xl bg-primary px-6 py-2.5 text-sm font-semibold text-white transition-default hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? '检索中...' : '检索'}
          </button>
        </div>
      </form>
      </section>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="flex items-center justify-between px-1">
            <h2 className="font-heading text-2xl font-semibold text-primary">
              检索结果 <span className="text-muted font-normal">({result.results.length})</span>
            </h2>
          </div>

          {result.results.length === 0 ? (
            <div className="paper-panel rounded-3xl p-14 text-center">
              <SearchIcon className="mx-auto mb-3 h-10 w-10 text-muted" />
              <p className="text-sm text-muted">未找到相关内容</p>
            </div>
          ) : (
            <div className="space-y-3">
              {result.results.map((item, idx) => (
                <article key={item.chunk_id} className="paper-panel rounded-2xl p-5 transition-default hover:border-accent/60">
                  <div className="mb-3 flex items-start justify-between gap-4">
                    <div className="flex min-w-0 items-center gap-2 text-sm">
                      <span className="inline-flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-accent/15 text-xs font-bold text-accent">
                        {idx + 1}
                      </span>
                      <span className="truncate font-semibold text-primary">{item.filename}</span>
                      {item.page_number && (
                        <span className="flex-shrink-0 text-muted">第 {item.page_number} 页</span>
                      )}
                    </div>
                    <span className="rounded-full bg-primary/5 px-2.5 py-1 font-mono text-xs text-muted">
                      {(item.score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p className="line-clamp-4 text-sm leading-7 text-secondary">{item.text}</p>
                </article>
              ))}
            </div>
          )}

          {result.citations.length > 0 && (
            <div className="paper-panel rounded-3xl p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-primary">
                <Quote className="h-4 w-4 text-accent" />
                引用来源
              </h3>
              <div className="space-y-2">
                {result.citations.map((cite) => (
                  <div key={cite.index} className="flex items-start gap-3 rounded-xl bg-white/65 p-3 text-sm">
                    <span className="mt-0.5 inline-flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-white">
                      {cite.index}
                    </span>
                    <div className="min-w-0">
                      <span className="font-semibold text-primary">{cite.filename}</span>
                      {cite.page_number && <span className="text-muted ml-1">第 {cite.page_number} 页</span>}
                      <p className="mt-0.5 line-clamp-1 text-xs text-muted">{cite.text_preview}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

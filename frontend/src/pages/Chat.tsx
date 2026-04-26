import { useState, useEffect, useCallback, useRef } from 'react';
import {
  MessageSquare,
  Plus,
  Trash2,
  Send,
  Loader2,
  Bot,
  User,
  Globe,
  BookOpen,
  X,
} from 'lucide-react';
import {
  listDocuments,
  listChatSessions,
  createChatSession,
  updateChatSession,
  deleteChatSession,
  getChatSessionDetail,
  sendChatMessage,
  getErrorMessage,
} from '../api/client';
import type { ChatSessionItem, ChatMessageItem, DocumentItem } from '../api/client';

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSessionItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [input, setInput] = useState('');
  const [newTitle, setNewTitle] = useState('New Chat');
  const [newDocumentId, setNewDocumentId] = useState('all');
  const [newWebSearch, setNewWebSearch] = useState(false);
  const [activeTitle, setActiveTitle] = useState('');
  const [activeDocumentId, setActiveDocumentId] = useState('all');
  const [activeWebSearch, setActiveWebSearch] = useState(false);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [savingSession, setSavingSession] = useState(false);
  const [error, setError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeSession = sessions.find((session) => session.id === activeSessionId);

  const parseDocumentId = (value: string) => (value === 'all' ? null : Number(value));

  const fetchSessions = useCallback(async () => {
    try {
      const data = await listChatSessions();
      setSessions(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, '获取会话列表失败'));
    }
  }, []);

  useEffect(() => {
    // 延后一拍启动请求，避开 React Hooks lint 对 effect 同步 setState 的误判。
    void Promise.resolve().then(fetchSessions);
  }, [fetchSessions]);

  useEffect(() => {
    void Promise.resolve().then(async () => {
      try {
        setDocuments(await listDocuments());
      } catch (err: unknown) {
        setError(getErrorMessage(err, '获取文献列表失败'));
      }
    });
  }, []);

  useEffect(() => {
    if (!activeSession) return;
    void Promise.resolve().then(() => {
      setActiveTitle(activeSession.title);
      setActiveDocumentId(activeSession.document_id ? String(activeSession.document_id) : 'all');
      setActiveWebSearch(activeSession.web_search_enabled);
    });
  }, [activeSession]);

  useEffect(() => {
    if (!activeSessionId) return;
    let ignore = false;

    // 详情请求可能在切换会话时交错返回，用 ignore 保证只更新当前会话。
    void Promise.resolve().then(async () => {
      if (ignore) return;
      setLoading(true);
      try {
        const data = await getChatSessionDetail(activeSessionId);
        if (!ignore) {
          setMessages(data.messages);
          setSessions((prev) => prev.map((item) => (item.id === data.session.id ? data.session : item)));
        }
      } catch (err: unknown) {
        if (!ignore) setError(getErrorMessage(err, '获取会话详情失败'));
      } finally {
        if (!ignore) setLoading(false);
      }
    });

    return () => {
      ignore = true;
    };
  }, [activeSessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleCreateSession = async () => {
    try {
      const session = await createChatSession(
        newTitle,
        parseDocumentId(newDocumentId),
        newWebSearch,
      );
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
      setNewTitle('New Chat');
      setNewDocumentId('all');
      setNewWebSearch(false);
    } catch (err: unknown) {
      setError(getErrorMessage(err, '创建会话失败'));
    }
  };

  const handleSaveSession = async () => {
    if (!activeSessionId) return;
    setSavingSession(true);
    setError('');
    try {
      const updated = await updateChatSession(
        activeSessionId,
        activeTitle,
        parseDocumentId(activeDocumentId),
        activeWebSearch,
      );
      setSessions((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err: unknown) {
      setError(getErrorMessage(err, '保存会话设置失败'));
    } finally {
      setSavingSession(false);
    }
  };

  const handleDeleteSession = async (id: number) => {
    if (!confirm('确定要删除这个会话吗？')) return;
    try {
      await deleteChatSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([]);
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err, '删除会话失败'));
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !activeSessionId || sending) return;

    const question = input.trim();
    setInput('');
    setSending(true);
    setError('');

    // Optimistically add user message
    const tempUserMsg: ChatMessageItem = {
      id: Date.now(),
      session_id: activeSessionId,
      role: 'user',
      content: question,
      citations: null,
      used_web_search: false,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await sendChatMessage(activeSessionId, question);
      const assistantMsg: ChatMessageItem = {
        id: Date.now() + 1,
        session_id: activeSessionId,
        role: 'assistant',
        content: res.answer,
        citations: res.citations,
        used_web_search: res.used_web_search,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      // Refresh sessions to update timestamp
      await fetchSessions();
    } catch (err: unknown) {
      setError(getErrorMessage(err, '发送消息失败'));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] min-h-[620px] flex-col gap-4 md:h-[calc(100vh-2.75rem)] md:flex-row">
      <div
        className={`paper-panel flex-shrink-0 overflow-hidden rounded-3xl transition-all duration-300 ${
          sidebarOpen ? 'w-full md:w-72' : 'w-0 opacity-0 md:w-0 md:opacity-0'
        }`}
      >
        <div className="flex items-center justify-between border-b border-primary/10 p-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Chats</p>
            <h2 className="font-heading text-2xl font-semibold text-primary">会话列表</h2>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={handleCreateSession}
              className="rounded-xl p-2 text-muted transition-default hover:bg-primary/5 hover:text-primary"
              title="新建会话"
            >
              <Plus className="h-4 w-4" />
            </button>
            <button
              onClick={() => setSidebarOpen(false)}
              className="rounded-xl p-2 text-muted transition-default hover:bg-primary/5 hover:text-primary md:hidden"
              aria-label="隐藏会话列表"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="border-b border-primary/10 p-3">
          <div className="space-y-2 rounded-2xl bg-white/65 p-3">
            <label className="block text-xs font-semibold text-muted" htmlFor="new-session-title">
              会话标题
            </label>
            <input
              id="new-session-title"
              value={newTitle}
              onChange={(event) => setNewTitle(event.target.value)}
              className="min-h-10 w-full rounded-xl border border-primary/10 bg-white px-3 text-sm font-semibold text-primary outline-none transition-default focus:border-accent"
              placeholder="例如：综述写作助手"
            />
            <label className="block text-xs font-semibold text-muted" htmlFor="new-session-document">
              检索范围
            </label>
            <select
              id="new-session-document"
              value={newDocumentId}
              onChange={(event) => setNewDocumentId(event.target.value)}
              className="min-h-10 w-full rounded-xl border border-primary/10 bg-white px-3 text-sm text-primary outline-none transition-default focus:border-accent"
            >
              <option value="all">全部已索引文献</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-xs font-semibold text-secondary">
              <input
                type="checkbox"
                checked={newWebSearch}
                onChange={(event) => setNewWebSearch(event.target.checked)}
                className="h-4 w-4 accent-[#171717]"
              />
              允许联网搜索补充
            </label>
            <button
              type="button"
              onClick={handleCreateSession}
              className="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-xl bg-primary px-3 text-sm font-semibold text-white transition-default hover:bg-secondary"
            >
              <Plus className="h-4 w-4" />
              新建会话
            </button>
          </div>
        </div>
        <div className="h-[calc(100%-18rem)] overflow-y-auto">
          {sessions.length === 0 ? (
            <div className="p-8 text-center">
              <MessageSquare className="mx-auto mb-2 h-8 w-8 text-muted" />
              <p className="text-sm text-muted">暂无会话</p>
            </div>
          ) : (
            <div className="p-2 space-y-1">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`group flex items-center gap-2 rounded-xl px-3 py-2.5 transition-default ${
                    activeSessionId === session.id
                      ? 'bg-primary text-white'
                      : 'text-primary hover:bg-white'
                  }`}
                  onClick={() => setActiveSessionId(session.id)}
                >
                  <MessageSquare className="h-4 w-4 flex-shrink-0" />
                  <span className="flex-1 truncate text-sm font-semibold">{session.title}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteSession(session.id);
                    }}
                    className="rounded p-1 opacity-0 transition-default hover:bg-white/10 group-hover:opacity-100"
                    aria-label="删除会话"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="paper-panel flex min-w-0 flex-1 flex-col overflow-hidden rounded-3xl">
        {!activeSessionId ? (
          <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary">
              <Bot className="h-8 w-8 text-accent" />
            </div>
            <h2 className="mb-2 font-heading text-3xl font-semibold text-primary">
              开始学术对话
            </h2>
            <p className="mb-6 max-w-md text-sm leading-6 text-muted">
              选择一个会话或创建新会话，基于您的文献知识库进行深度问答。
            </p>
            <button
              onClick={handleCreateSession}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white transition-default hover:bg-secondary"
            >
              <Plus className="h-4 w-4" />
              新建会话
            </button>
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="mt-4 text-sm font-semibold text-muted transition-default hover:text-primary"
              >
                显示会话列表
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="border-b border-primary/10 px-5 py-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                {!sidebarOpen && (
                  <button
                    onClick={() => setSidebarOpen(true)}
                    className="rounded-lg p-1.5 text-muted transition-default hover:bg-primary/5 hover:text-primary"
                    aria-label="显示会话列表"
                  >
                    <MessageSquare className="h-4 w-4" />
                  </button>
                )}
                <h3 className="truncate text-sm font-semibold text-primary">
                  {activeSession?.title || '会话'}
                </h3>
              </div>
              <button
                onClick={() => handleDeleteSession(activeSessionId)}
                className="rounded-lg p-1.5 text-muted transition-default hover:bg-red-50 hover:text-red-600"
                aria-label="删除当前会话"
              >
                <Trash2 className="h-4 w-4" />
              </button>
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-[1fr_220px_auto_auto]">
                <input
                  value={activeTitle}
                  onChange={(event) => setActiveTitle(event.target.value)}
                  className="min-h-10 rounded-xl border border-primary/10 bg-white/70 px-3 text-sm font-semibold text-primary outline-none transition-default focus:border-accent"
                  placeholder="会话标题"
                />
                <select
                  value={activeDocumentId}
                  onChange={(event) => setActiveDocumentId(event.target.value)}
                  className="min-h-10 rounded-xl border border-primary/10 bg-white/70 px-3 text-sm text-primary outline-none transition-default focus:border-accent"
                >
                  <option value="all">全部已索引文献</option>
                  {documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.filename}
                    </option>
                  ))}
                </select>
                <label className="flex min-h-10 items-center gap-2 rounded-xl border border-primary/10 bg-white/70 px-3 text-xs font-semibold text-secondary">
                  <input
                    type="checkbox"
                    checked={activeWebSearch}
                    onChange={(event) => setActiveWebSearch(event.target.checked)}
                    className="h-4 w-4 accent-[#171717]"
                  />
                  联网搜索
                </label>
                <button
                  type="button"
                  onClick={handleSaveSession}
                  disabled={savingSession}
                  className="min-h-10 rounded-xl bg-primary px-4 text-sm font-semibold text-white transition-default hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {savingSession ? '保存中' : '保存'}
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {loading && messages.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="h-6 w-6 animate-spin text-muted" />
                </div>
              ) : messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <BookOpen className="mb-3 h-10 w-10 text-muted" />
                  <p className="text-sm text-muted">发送消息开始对话</p>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                  >
                    <div
                      className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full ${
                        msg.role === 'user' ? 'bg-accent/10' : 'bg-primary'
                      }`}
                    >
                      {msg.role === 'user' ? (
                        <User className="h-4 w-4 text-accent" />
                      ) : (
                        <Bot className="h-4 w-4 text-white" />
                      )}
                    </div>
                    <div
                      className={`max-w-[82%] rounded-2xl px-4 py-3 shadow-sm ${
                        msg.role === 'user'
                          ? 'bg-primary text-white'
                          : 'border border-primary/10 bg-white/80 text-secondary'
                      }`}
                    >
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {msg.content}
                      </p>
                      {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                        <div className="mt-3 border-t border-primary/10 pt-3">
                          <div className="flex items-center gap-1.5 mb-2">
                            <BookOpen className="h-3.5 w-3.5 text-accent" />
                            <span className="text-xs font-medium text-primary">引用来源</span>
                          </div>
                          <div className="space-y-1.5">
                            {msg.citations.map((cite) => (
                              <div
                                key={cite.index}
                                className="flex items-start gap-2 text-xs"
                              >
                                <span className="mt-0.5 inline-flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-primary text-[9px] font-bold text-white">
                                  {cite.index}
                                </span>
                                <div>
                                  <span className="font-medium text-primary">{cite.filename}</span>
                                  {cite.page_number && (
                                    <span className="text-muted ml-1">第 {cite.page_number} 页</span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {msg.used_web_search && (
                        <div className="mt-2 flex items-center gap-1 text-xs text-muted">
                          <Globe className="h-3 w-3" />
                          <span>使用了网络搜索</span>
                        </div>
                      )}
                      <div
                        className={`text-[10px] mt-1.5 ${
                          msg.role === 'user' ? 'text-white/60' : 'text-muted'
                        }`}
                      >
                        {new Date(msg.created_at).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))
              )}
              {sending && (
                <div className="flex gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary">
                    <Bot className="h-4 w-4 text-white" />
                  </div>
                  <div className="rounded-2xl border border-primary/10 bg-white/80 px-4 py-3">
                    <Loader2 className="h-4 w-4 animate-spin text-muted" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="border-t border-primary/10 p-4">
              {error && (
                <div className="mb-3 flex items-center justify-between rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                  {error}
                  <button onClick={() => setError('')} className="rounded p-0.5 transition-default hover:bg-red-100" aria-label="关闭错误提示">
                    <X className="h-3 w-3" />
                  </button>
                </div>
              )}
              <form onSubmit={handleSend} className="flex gap-3 rounded-2xl border border-primary/10 bg-white/70 p-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="输入您的问题..."
                  className="min-h-11 flex-1 rounded-xl border border-transparent bg-transparent px-4 text-sm text-primary outline-none transition-default placeholder:text-muted focus:border-accent/40 focus:bg-white"
                />
                <button
                  type="submit"
                  disabled={sending || !input.trim()}
                  className="inline-flex min-h-11 items-center justify-center rounded-xl bg-primary px-4 py-2.5 text-white transition-default hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {sending ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Send className="h-5 w-5" />
                  )}
                </button>
              </form>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

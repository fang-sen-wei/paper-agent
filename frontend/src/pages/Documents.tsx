import { useState, useEffect, useCallback } from 'react';
import { Upload, Trash2, FileText, Loader2, Layers, Database, ChevronDown, ChevronUp, X } from 'lucide-react';
import {
  listDocuments,
  uploadDocuments,
  deleteDocument,
  processDocument,
  indexDocument,
  getDocumentChunks,
  getErrorMessage,
} from '../api/client';
import type { DocumentItem, DocumentChunkItem } from '../api/client';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [chunks, setChunks] = useState<DocumentChunkItem[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [expandedDoc, setExpandedDoc] = useState<number | null>(null);
  const [actionDocId, setActionDocId] = useState<number | null>(null);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (err: unknown) {
      setError(getErrorMessage(err, '获取文献列表失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 延后一拍启动请求，避免 hooks lint 将加载状态更新视为同步 effect 更新。
    void Promise.resolve().then(fetchDocs);
  }, [fetchDocs]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    setError('');
    try {
      await uploadDocuments(files);
      await fetchDocs();
      e.target.value = '';
    } catch (err: unknown) {
      setError(getErrorMessage(err, '上传失败'));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这篇文献吗？')) return;
    try {
      await deleteDocument(id);
      await fetchDocs();
      if (expandedDoc === id) setExpandedDoc(null);
    } catch (err: unknown) {
      setError(getErrorMessage(err, '删除失败'));
    }
  };

  const handleProcess = async (id: number) => {
    setActionDocId(id);
    setError('');
    try {
      await processDocument(id);
      await fetchDocs();
    } catch (err: unknown) {
      setError(getErrorMessage(err, '解析或索引失败'));
    } finally {
      setActionDocId(null);
    }
  };

  const handleIndex = async (id: number) => {
    setActionDocId(id);
    setError('');
    try {
      await indexDocument(id);
      await fetchDocs();
    } catch (err: unknown) {
      setError(getErrorMessage(err, '索引失败'));
    } finally {
      setActionDocId(null);
    }
  };

  const toggleChunks = async (id: number) => {
    if (expandedDoc === id) {
      setExpandedDoc(null);
      return;
    }
    setExpandedDoc(id);
    setChunksLoading(true);
    try {
      const data = await getDocumentChunks(id);
      setChunks(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, '获取切片失败'));
    } finally {
      setChunksLoading(false);
    }
  };

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      pending: 'bg-amber-50 text-amber-700 border-amber-200',
      processing: 'bg-blue-50 text-blue-700 border-blue-200',
      completed: 'bg-cyan-50 text-cyan-700 border-cyan-200',
      indexed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      failed: 'bg-red-50 text-red-700 border-red-200',
    };
    const labels: Record<string, string> = {
      pending: '待处理',
      processing: '处理中',
      completed: '已解析',
      indexed: '已索引',
      failed: '失败',
    };
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${map[status] || 'bg-gray-50 text-gray-600 border-gray-200'}`}>
        {labels[status] || status}
      </span>
    );
  };

  return (
    <div className="space-y-5 md:space-y-6">
      <div className="paper-panel rounded-3xl p-6 md:p-8">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent">Library</p>
            <h1 className="mt-2 font-heading text-4xl font-semibold text-primary">文献管理</h1>
            <p className="mt-2 text-sm leading-6 text-muted">上传文献后执行解析并索引，确保后续检索和对话可以命中文献内容。</p>
          </div>
          <label className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white transition-default hover:bg-secondary disabled:opacity-50">
            <Upload className="h-4 w-4" />
            {uploading ? '上传中...' : '上传文献'}
            <input type="file" multiple className="hidden" onChange={handleUpload} disabled={uploading} />
          </label>
        </div>
      </div>

      {error && (
        <div className="flex items-center justify-between rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
          <button onClick={() => setError('')} className="rounded-lg p-1 transition-default hover:bg-red-100" aria-label="关闭错误提示">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="paper-panel overflow-hidden rounded-3xl">
        <div className="flex items-center justify-between border-b border-primary/10 px-5 py-4">
          <div>
            <h2 className="font-heading text-2xl font-semibold text-primary">资料库</h2>
            <p className="mt-1 text-xs text-muted">{documents.length} 篇文献</p>
          </div>
          <div className="hidden items-center gap-2 text-xs text-muted sm:flex">
            <span className="h-2 w-2 rounded-full bg-accent" />
            解析后自动索引
          </div>
        </div>
        {loading && documents.length === 0 ? (
          <div className="p-14 text-center">
            <Loader2 className="mx-auto mb-3 h-8 w-8 animate-spin text-muted" />
            <p className="text-sm text-muted">加载中...</p>
          </div>
        ) : documents.length === 0 ? (
          <div className="p-14 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/5">
              <FileText className="h-7 w-7 text-muted" />
            </div>
            <p className="font-semibold text-primary">暂无文献</p>
            <p className="mt-1 text-sm text-muted">请先上传 PDF、Word 或 TXT 资料。</p>
          </div>
        ) : (
          <div className="divide-y divide-primary/10">
            {documents.map((doc) => (
              <div key={doc.id} className="p-4 md:p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex min-w-0 flex-1 items-start gap-3">
                    <div className="mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary/5">
                      <FileText className="h-5 w-5 text-secondary" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="truncate text-sm font-semibold text-primary">{doc.filename}</h3>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        {statusBadge(doc.status)}
                        <span className="text-xs text-muted">{new Date(doc.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-shrink-0 items-center gap-1">
                    {(doc.status === 'pending' || doc.status === 'failed') && (
                      <button
                        onClick={() => handleProcess(doc.id)}
                        disabled={actionDocId === doc.id}
                        className="rounded-lg p-2 text-muted transition-default hover:bg-primary/5 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                        title="解析并索引"
                      >
                        {actionDocId === doc.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Layers className="h-4 w-4" />}
                      </button>
                    )}
                    {(doc.status === 'completed' || doc.status === 'indexed') && (
                      <button
                        onClick={() => handleIndex(doc.id)}
                        disabled={actionDocId === doc.id}
                        className="rounded-lg p-2 text-muted transition-default hover:bg-primary/5 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                        title={doc.status === 'indexed' ? '重建索引' : '构建索引'}
                      >
                        {actionDocId === doc.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
                      </button>
                    )}
                    <button
                      onClick={() => toggleChunks(doc.id)}
                      className="rounded-lg p-2 text-muted transition-default hover:bg-primary/5 hover:text-primary"
                      title="查看切片"
                    >
                      {expandedDoc === doc.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="rounded-lg p-2 text-muted transition-default hover:bg-red-50 hover:text-red-600"
                      title="删除"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {expandedDoc === doc.id && (
                  <div className="mt-4 pl-0 md:pl-[52px]">
                    {chunksLoading ? (
                      <div className="py-4 text-center">
                        <Loader2 className="mx-auto h-5 w-5 animate-spin text-muted" />
                      </div>
                    ) : chunks.length === 0 ? (
                      <p className="py-2 text-sm text-muted">暂无切片数据</p>
                    ) : (
                      <div className="max-h-80 space-y-2 overflow-y-auto pr-2">
                        {chunks.map((chunk) => (
                          <div key={chunk.id} className="rounded-xl border border-primary/10 bg-white/65 p-3 text-sm">
                            <div className="mb-1 flex items-center gap-2">
                              <span className="font-mono text-xs text-muted">#{chunk.chunk_index}</span>
                              {chunk.page_number && (
                                <span className="text-xs text-muted">第 {chunk.page_number} 页</span>
                              )}
                            </div>
                            <p className="text-sm leading-7 text-secondary">{chunk.text}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

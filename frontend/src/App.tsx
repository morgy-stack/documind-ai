import { useEffect, useRef, useState } from 'react'
import { Bot, FileText, UploadCloud, Send, Trash2, Sparkles, BookOpen, Plus, LoaderCircle, FlaskConical, Paperclip } from 'lucide-react'

type Doc = { id: string; filename: string; chunks: number; uploaded_at: string }
type Source = { filename: string; page: number | null; excerpt: string; chunk_id: string }
type Message = { role: 'user' | 'assistant'; content: string; sources?: Source[] }

const API = '/api'

async function readJson(response: Response) {
  try {
    return await response.json()
  } catch {
    const detail = response.status === 413 ? 'File is too large to upload.' : `Server error (${response.status}).`
    return { detail }
  }
}

export default function App() {
  const [documents, setDocuments] = useState<Doc[]>([])
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hello! I’m DocuMind. Upload a document, then ask me anything about its contents. I’ll show the passages I used so you can verify the answer.' }
  ])
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [showSources, setShowSources] = useState(true)
  const [mode, setMode] = useState<'demo' | 'openai' | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  async function loadDocuments() {
    try {
      const response = await fetch(`${API}/documents`)
      if (response.ok) setDocuments(await response.json())
    } catch { /* API may still be starting */ }
  }

  useEffect(() => {
    void loadDocuments()
    fetch(`${API}/health`).then(r => r.json()).then(d => setMode(d.mode ?? null)).catch(() => { /* API may still be starting */ })
  }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  async function uploadFile(file?: File) {
    if (!file) return
    const form = new FormData()
    form.append('file', file)
    await indexDocument(`${API}/documents/upload`, form)
  }

  async function indexDocument(url: string, body?: FormData) {
    setError('')
    setUploading(true)
    try {
      const response = await fetch(url, { method: 'POST', body })
      const data = await readJson(response)
      if (!response.ok) throw new Error(data.detail || 'Upload failed.')
      await loadDocuments()
      setMessages(prev => [...prev, { role: 'assistant', content: `I’ve indexed **${data.filename}** into ${data.chunks} searchable text chunks. You can ask questions about it now.` }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to upload document.')
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  async function removeDocument(doc: Doc) {
    if (!window.confirm(`Remove ${doc.filename} from the knowledge base?`)) return
    try {
      const response = await fetch(`${API}/documents/${doc.id}`, { method: 'DELETE' })
      const data = await readJson(response)
      if (!response.ok) throw new Error(data.detail || 'Delete failed.')
      await loadDocuments()
      setMessages(prev => [...prev, { role: 'assistant', content: `Removed **${doc.filename}** from the knowledge base.` }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete document.')
    }
  }

  async function sendQuestion(text = question) {
    const trimmed = text.trim()
    if (!trimmed || busy) return
    setError('')
    setQuestion('')
    setMessages(prev => [...prev, { role: 'user', content: trimmed }])
    setBusy(true)
    try {
      const response = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmed }),
      })
      const data = await readJson(response)
      if (!response.ok) throw new Error(data.detail || 'Unable to answer question.')
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer, sources: data.sources }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to send question.')
    } finally {
      setBusy(false)
    }
  }

  const suggestions = ['Summarize this document', 'What are the key requirements?', 'Find important dates and deadlines']

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Sparkles size={19} /></div><div><strong>DocuMind</strong><span>AI WORKSPACE</span></div></div>
        <button className="new-chat" onClick={() => setMessages([{ role: 'assistant', content: 'New conversation started. Your indexed documents are still available—what would you like to know?' }])}><Plus size={17} /> New conversation</button>
        <div className="side-label"><span>KNOWLEDGE BASE</span><button title="Upload document" onClick={() => fileInput.current?.click()}><Plus size={16} /></button></div>
        <div className="doc-list">
          {documents.length === 0 && <div className="empty-docs">Your knowledge base is empty. Upload a file to get started.</div>}
          {documents.map(doc => <div className="doc-row" key={doc.id}><FileText size={17} /><div className="doc-info"><strong title={doc.filename}>{doc.filename}</strong><span>{doc.chunks} chunks</span></div><button className="icon-button delete" title="Remove document" onClick={() => void removeDocument(doc)}><Trash2 size={15} /></button></div>)}
        </div>
        <div className="sidebar-bottom"><div className={`status-dot${mode === 'demo' ? ' demo' : ''}`} /> Local workspace <span>•</span> {mode === 'demo' ? 'Demo mode' : 'RAG enabled'}</div>
      </aside>

      <main className="main-panel">
        <header className="topbar"><div className="mobile-brand"><Bot size={20} /> DocuMind AI</div><div className="topbar-right"><span className="model-pill" title={mode === 'demo' ? 'No OpenAI API key is set, so answers quote the most relevant passages instead of being written by an AI model.' : undefined}><span className={`status-dot${mode === 'demo' ? ' demo' : ''}`} /> {mode === 'demo' ? 'Demo mode · no API key' : 'AI assistant online'}</span><button className="source-toggle" onClick={() => setShowSources(v => !v)}><BookOpen size={16} /> {showSources ? 'Sources on' : 'Sources off'}</button></div></header>
        <section className="chat-area">
          <div className="welcome-heading"><div className="welcome-icon"><Sparkles size={22} /></div><p className="eyebrow">YOUR DOCUMENT INTELLIGENCE</p><h1>Ask your documents<br /><span>anything.</span></h1><p className="welcome-copy">Get grounded answers from your files, with source passages you can verify.</p></div>

          {documents.length === 0 && <div className="upload-card"><div className="upload-icon"><UploadCloud size={23} /></div><div><strong>Start with your documents</strong><p>Upload PDF, DOCX, or TXT files (up to 15 MB each), or try the bundled sample handbook.</p></div><button className="secondary-button" onClick={() => void indexDocument(`${API}/documents/sample`)} disabled={uploading}><FlaskConical size={16} /> Try sample</button><button className="primary-button" onClick={() => fileInput.current?.click()} disabled={uploading}>{uploading ? <LoaderCircle className="spin" size={16} /> : <UploadCloud size={16} />} Upload files</button></div>}

          <div className="messages">
            {messages.map((message, index) => <div className={`message ${message.role}`} key={index}><div className="avatar">{message.role === 'assistant' ? <Bot size={18} /> : 'You'}</div><div className="message-body"><div className="message-name">{message.role === 'assistant' ? 'DocuMind AI' : 'You'}</div><div className="message-text">{message.content.split(/\*\*(.*?)\*\*/g).map((part, i) => i % 2 ? <strong key={i}>{part}</strong> : part)}</div>{showSources && message.sources && message.sources.length > 0 && <div className="sources"><div className="sources-title"><BookOpen size={14} /> SOURCES USED</div>{message.sources.map((source, i) => <div className="source-card" key={source.chunk_id || i}><div className="source-meta"><FileText size={14} /><strong>{source.filename}</strong><span>{source.page ? `Page ${source.page}` : 'Document passage'}</span></div><p>{source.excerpt}{source.excerpt.length >= 500 ? '…' : ''}</p></div>)}</div>}</div></div>)}
            {busy && <div className="message assistant"><div className="avatar"><Bot size={18} /></div><div className="message-body"><div className="message-name">DocuMind AI</div><div className="thinking"><span /><span /><span /> Searching documents and composing an answer</div></div></div>}
            <div ref={bottomRef} />
          </div>
          {error && <div className="error-banner">{error}</div>}
          <div className="composer-wrap">
            {messages.length < 3 && documents.length > 0 && <div className="suggestions">{suggestions.map(item => <button key={item} onClick={() => void sendQuestion(item)}>{item}</button>)}</div>}
            <form className="composer" onSubmit={e => { e.preventDefault(); void sendQuestion() }}><button type="button" className="attach-button" onClick={() => fileInput.current?.click()} disabled={uploading} title="Upload a PDF, DOCX or TXT file" aria-label="Upload document">{uploading ? <LoaderCircle className="spin" size={18} /> : <Paperclip size={18} />}<span>Upload</span></button><textarea value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void sendQuestion() } }} placeholder="Ask a question about your documents…" rows={1} /><button className="send-button" disabled={!question.trim() || busy} aria-label="Send question"><Send size={18} /></button></form>
            <div className="composer-foot"><span><span className="status-dot" /> Answers are grounded in retrieved document passages</span><span>Enter to send · Shift + Enter for newline</span></div>
          </div>
        </section>
      </main>
      <input ref={fileInput} type="file" accept=".pdf,.docx,.txt" hidden onChange={e => void uploadFile(e.target.files?.[0])} />
    </div>
  )
}

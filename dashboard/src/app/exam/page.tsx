'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import Logo from '@/components/Logo';
import ThemeToggle from '@/components/ThemeToggle';
import './exam.css';

type Assessment = { id: string; status: string; percent: number; correct: number; needs_training: number; pass_percent: number };
type Question = { id: number; question: string; options: string[] };

async function action(body: Record<string, unknown>) {
  const response = await fetch('/api/exam', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Please try again.');
  return data;
}

export default function AssessmentPage() {
  const { user, isLoading } = useAuth();
  const [exam, setExam] = useState<Assessment | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<Assessment | null>(null);
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const root = useRef<HTMLElement>(null);
  const lastEvent = useRef<Record<string, number>>({});
  const completed = useRef(false);
  const active = questions.length > 0 && !result;
  useEffect(() => {
    if (user?.role !== 'employee') return;
    const controller = new AbortController();
    fetch('/api/exam', { cache: 'no-store', signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('Could not load your assessment. Refresh to retry.');
      const body = await response.json();
      if (!controller.signal.aborted) { setExam(body.exam); setLoaded(true); }
    }).catch(err => { if (!controller.signal.aborted) setError(err.message); });
    return () => controller.abort();
  }, [user?.role]);

  useEffect(() => {
    if (!active || !exam) return;
    const record = (kind: string) => {
      if (completed.current) return;
      if (Date.now() - (lastEvent.current[kind] || 0) < 2000) return;
      lastEvent.current[kind] = Date.now();
      setNotice('A browser activity event was recorded for your administrator. Your answers are still here.');
      void action({ action: 'violation', examId: exam.id, kind }).catch(() => setNotice('Activity logging is temporarily unavailable. Please keep this tab open.'));
    };
    const visibility = () => { if (document.hidden) record('tab_hidden'); };
    const blur = () => record('window_blur');
    const fullscreen = () => { if (!document.fullscreenElement) record('fullscreen_exit'); };
    const clipboard = (event: Event) => { event.preventDefault(); record(event.type === 'contextmenu' ? 'context_menu' : event.type); };
    const area = root.current;
    document.addEventListener('visibilitychange', visibility);
    document.addEventListener('fullscreenchange', fullscreen);
    window.addEventListener('blur', blur);
    ['copy','cut','paste','contextmenu'].forEach(kind => area?.addEventListener(kind, clipboard));
    return () => {
      document.removeEventListener('visibilitychange', visibility);
      document.removeEventListener('fullscreenchange', fullscreen);
      window.removeEventListener('blur', blur);
      ['copy','cut','paste','contextmenu'].forEach(kind => area?.removeEventListener(kind, clipboard));
    };
  }, [active, exam]);

  async function start() {
    if (!exam) return;
    setBusy(true); setError('');
    // Fullscreen requires this user gesture and may be unavailable in some browsers.
    const fullscreen = root.current?.requestFullscreen?.().catch(() => setNotice('Fullscreen is unavailable. Stay in this tab while answering.'));
    try {
      const data = await action({ action: 'start', examId: exam.id });
      if (data.result) setResult(data.result);
      else setQuestions(data.questions);
      await fullscreen;
    } catch (err) { setError(err instanceof Error ? err.message : 'Please retry.'); }
    finally { setBusy(false); }
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!exam || questions.some(q => answers[q.id] === undefined)) { setError('Answer every question first.'); return; }
    setBusy(true); setError('');
    try {
      const data = await action({ action: 'submit', examId: exam.id, answers: questions.map(q => answers[q.id]) });
      completed.current = true;
      setResult(data.result);
      if (document.fullscreenElement) await document.exitFullscreen().catch(() => {});
    } catch (err) { setError(err instanceof Error ? err.message : 'Please retry.'); }
    finally { setBusy(false); }
  }
  const question = questions[index];
  return <main className="exam-page" ref={root}>
    <header className="exam-top"><Logo variant="full" size={36} /><ThemeToggle /></header>
    <section className="exam-card">
      {isLoading ? <p role="status">Loading…</p> : user?.role !== 'employee' ? <><h1>Sign in to continue</h1><p>Use your employee account to open your assessment.</p><Link className="btn btn-primary" href="/auth">Sign in</Link></>
      : result ? <><span className="exam-eyebrow">Assessment complete</span><h1>{result.percent}%</h1><p>{result.correct} of 15 correct · Pass threshold {result.pass_percent}%</p><p>{result.needs_training ? 'Your administrator will review your result and recommend training.' : 'You passed. Keep verifying unexpected requests and reporting suspicious links.'}</p><Link className="btn btn-primary" href="/">Return to dashboard</Link></>
      : !loaded ? <p role="status">Loading your assessment…</p>
      : !exam ? <><h1>You’re up to date</h1><p>No assessment is waiting for you.</p><Link className="btn btn-primary" href="/">Return to dashboard</Link></>
      : !active ? <><span className="exam-eyebrow">Security check-in</span><h1>A short refresher. A safer next click.</h1><p>Complete 15 questions after your recent phishing simulation. Your administrator reviews the result.</p><ul className="exam-rules"><li>Stay in this tab. Tab changes and fullscreen exits are recorded.</li><li>Copy and paste are disabled during the assessment.</li><li>This web page cannot prevent device screenshots or access to other apps.</li></ul><button className="btn btn-primary" disabled={busy} onClick={start}>{busy ? 'Starting…' : 'Start assessment'}</button></>
      : <form action="/api/exam" method="post" onSubmit={submit}>
          <div className="exam-progress"><span>Question {index + 1} / 15</span><span>{Object.keys(answers).length} answered</span></div>
          <progress max={15} value={Object.keys(answers).length} aria-label="Questions answered" />
          <fieldset className="exam-question" key={question.id}><legend>{question.question}</legend>{question.options.map((option, choice) => <label key={option} className="exam-option"><input type="radio" name={`question-${question.id}`} value={choice} checked={answers[question.id] === choice} onChange={() => setAnswers(previous => ({ ...previous, [question.id]: choice }))} /><span>{option}</span></label>)}</fieldset>
          <div className="exam-actions"><button type="button" className="btn" disabled={!index || busy} onClick={() => setIndex(index - 1)}>Previous</button>{index < 14 ? <button type="button" className="btn btn-primary" disabled={busy} onClick={() => setIndex(index + 1)}>Next question</button> : <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? 'Submitting…' : 'Submit assessment'}</button>}</div>
        </form>}
      {notice && <p className="exam-notice" role="status">{notice}</p>}
      {error && <p className="debt-error" role="alert">{error}</p>}
    </section>
  </main>;
}

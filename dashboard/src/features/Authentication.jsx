import { useEffect, useState } from 'react';
import { SignInButton, UserButton, useAuth } from '@clerk/react';
import { LockKeyhole, LogIn, RefreshCw, ShieldCheck } from 'lucide-react';
import { api } from './data';

const clerkPublishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
  || import.meta.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
export const authConfigured = Boolean(clerkPublishableKey?.startsWith('pk_'));
export function AccessGate({ authority = false, children }) {
  if (!authConfigured) return <div className="panel auth-card"><span className="auth-mark"><LockKeyhole size={28} /></span><span className="eyebrow">{authority ? 'PRIVATE OPERATOR WORKSPACE' : 'CONSENT-BASED COMMUNITY REPORTING'}</span><h2>{authority ? 'Operator access is not configured yet.' : 'Reporting sign-in is not configured yet.'}</h2><p>{authority ? 'An approved operator account and a verified session are required to access private evidence and case review.' : 'A verified account is required to submit a report. Public observations remain available without signing in.'}</p><div className="notice amber"><ShieldCheck size={17} /><span>Sign-in setup is pending. No private records can be accessed or submitted from this view.</span></div></div>;
  return <VerifiedAccess authority={authority}>{children}</VerifiedAccess>;
}
function VerifiedAccess({ authority, children }) {
  const { isLoaded, isSignedIn, userId, sessionId, getToken } = useAuth();
  const [verified, setVerified] = useState(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    setVerified(null); setError('');
    if (!isLoaded || !isSignedIn) return;
    const controller = new AbortController();
    let active = true;
    async function check() {
      try {
        const token = await getToken();
        if (!token) throw new Error('Your sign-in session could not be verified. Please sign in again.');
        const result = await api(authority ? '/api/v2/authority/session' : '/api/v2/session', { signal: controller.signal, headers: { Authorization: `Bearer ${token}` } });
        if (!(authority ? result.authorized === true : result.authenticated === true)) throw new Error('This account has not been authorized for this workspace.');
        if (active) { setVerified({ userId, sessionId, email: result.email }); setError(''); }
      } catch (err) { if (active && !controller.signal.aborted) { setVerified(null); setError(err.message); } }
    }
    check();
    const timer = setInterval(check, 60000);
    return () => { active = false; controller.abort(); clearInterval(timer); };
  }, [isLoaded, isSignedIn, userId, sessionId, getToken, authority, attempt]);
  if (!isLoaded) return <div className="route-loading"><RefreshCw className="spin" size={20} /> Loading secure sign-in…</div>;
  if (!isSignedIn) return <div className="panel auth-card"><span className="auth-mark"><LockKeyhole size={28} /></span><span className="eyebrow">{authority ? 'PRIVATE OPERATOR WORKSPACE' : 'YOUR OBSERVATION CAN HELP'}</span><h2>{authority ? 'Access for approved operators.' : 'Sign in to contribute.'}</h2><p>{authority ? 'Review private evidence, record decisions and manage model submissions. Access is checked against the server’s approved operator list.' : 'A verified account helps keep community evidence accountable. Your report is stored privately for human review.'}</p><SignInButton mode="modal" forceRedirectUrl={window.location.href}><button className="button primary"><LogIn size={16} />{authority ? 'Sign in as an operator' : 'Sign in to report'}</button></SignInButton></div>;
  if (error) return <div className="panel auth-card"><span className="auth-mark"><ShieldCheck size={28} /></span><h2>Access could not be verified.</h2><p>{error}</p><div className="form-actions"><button className="button secondary" onClick={() => setAttempt(n => n + 1)}><RefreshCw size={15} />Try verification again</button><UserButton /></div></div>;
  if (!verified || verified.userId !== userId || verified.sessionId !== sessionId) return <div className="route-loading"><RefreshCw className="spin" size={20} />Verifying access with the server…</div>;
  return <div key={`${userId}:${sessionId}`}><div className="auth-user"><UserButton /><span>{verified.email}</span><span className="status-badge authorized"><i />{authority ? 'Approved operator' : 'Verified account'}</span></div>{children}</div>;
}

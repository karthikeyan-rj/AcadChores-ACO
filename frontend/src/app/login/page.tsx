'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { Cpu, Mail, Lock, User, Loader2, AlertCircle } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { getBackendUrl } from '@/lib/config';

const GoogleSignIn = dynamic(() => import('./GoogleSignIn'), {
  ssr: false,
  loading: () => (
    <div className="w-[320px] h-[44px] bg-[#1b1f28] border border-border rounded-lg animate-pulse mx-auto" />
  ),
});

function LoginForm() {
  const { user, login, register } = useAuth();
  const router = useRouter();

  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) router.replace('/dashboard');
  }, [user, router]);

  const handleGoogleSuccess = async (credential: string) => {
    setError('');
    setSubmitting(true);
    try {
      const res = await fetch(`${getBackendUrl()}/api/v1/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Google login failed');
      }
      const data = await res.json();
      localStorage.setItem('aco_token', data.access_token);
      localStorage.setItem('aco_user', JSON.stringify(data.user));
      window.location.href = '/dashboard';
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      if (isSignUp) {
        await register(email, name, password);
      } else {
        await login(email, password);
      }
      router.replace('/dashboard');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <div className="w-full max-w-md mx-auto flex flex-col justify-center px-8">
        <div className="flex items-center gap-3 mb-10">
          <Cpu className="text-primary h-10 w-10 animate-pulse" />
          <div>
            <h1 className="font-bold text-2xl tracking-wide">ACO Operator</h1>
            <p className="text-xs text-gray-400">Autonomous Computer Operator v1.0</p>
          </div>
        </div>

        <h2 className="text-xl font-bold mb-6">
          {isSignUp ? 'Create Account' : 'Sign In'}
        </h2>

        {error && (
          <div className="bg-danger/10 border border-danger/30 text-danger text-sm rounded-lg p-3 mb-4 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <div className="mb-4 flex justify-center">
          {submitting ? (
            <div className="w-full flex items-center justify-center gap-2 bg-[#1b1f28] border border-border rounded-xl py-3 text-sm text-gray-300">
              <Loader2 className="h-4 w-4 animate-spin" />
              Signing in...
            </div>
          ) : (
            <GoogleSignIn onSuccess={handleGoogleSuccess} onError={() => setError('Google sign-in was cancelled or failed.')} />
          )}
        </div>

        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px bg-border" />
          <span className="text-xs text-gray-500">or continue with email</span>
          <div className="flex-1 h-px bg-border" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {isSignUp && (
            <div className="relative">
              <User className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
              <input
                type="text"
                placeholder="Full name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full pl-10 pr-4 py-3 text-sm bg-card border border-border rounded-xl outline-none focus:border-primary transition"
                required
              />
            </div>
          )}
          <div className="relative">
            <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full pl-10 pr-4 py-3 text-sm bg-card border border-border rounded-xl outline-none focus:border-primary transition"
              required
            />
          </div>
          <div className="relative">
            <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full pl-10 pr-4 py-3 text-sm bg-card border border-border rounded-xl outline-none focus:border-primary transition"
              required
              minLength={6}
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-primary hover:bg-primary/95 text-white font-semibold py-3 rounded-xl shadow-lg disabled:opacity-40 transition flex items-center justify-center gap-2"
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : isSignUp ? (
              'Create Account'
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <p className="text-xs text-gray-500 text-center mt-6">
          {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            onClick={() => { setIsSignUp(!isSignUp); setError(''); }}
            className="text-primary hover:underline"
          >
            {isSignUp ? 'Sign In' : 'Sign Up'}
          </button>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return <LoginForm />;
}

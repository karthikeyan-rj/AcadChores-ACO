'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { Cpu, Mail, Lock, User, Loader2, AlertCircle } from 'lucide-react';
import { useAuth } from '@/lib/auth';

const GoogleSignIn = dynamic(() => import('./GoogleSignIn'), {
  ssr: false,
  loading: () => (
    <div className="w-[320px] h-[44px] bg-input border border-theme rounded-xl animate-pulse mx-auto" />
  ),
});

function LoginForm() {
  const { user, login, register, loginWithGoogle } = useAuth();
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
      await loginWithGoogle(credential);
      router.replace('/dashboard');
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
    <div className="flex h-screen w-screen overflow-hidden bg-app text-theme">
      <div className="w-full max-w-md mx-auto flex flex-col justify-center px-8 relative z-10">
        {/* Brand mark */}
        <div className="flex items-center gap-3 mb-10">
          <div className="w-12 h-12 rounded-2xl bg-surface-2 border border-theme flex items-center justify-center">
            <Cpu className="text-theme h-6 w-6" />
          </div>
          <div>
            <h1 className="font-bold text-2xl tracking-wide text-theme">ACO Operator</h1>
            <p className="text-xs text-theme-tertiary">Autonomous Computer Operator v1.0</p>
          </div>
        </div>

        {/* Auth card */}
        <div className="bg-surface border border-theme rounded-[14px] shadow-theme-lg p-8">
          <h2 className="text-xl font-bold mb-6 text-theme">
            {isSignUp ? 'Create Account' : 'Sign In'}
          </h2>

          {error && (
            <div className="bg-status-error-soft border border-status-error text-status-error text-sm rounded-xl p-3 mb-4 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <div className="mb-4 flex justify-center">
            {submitting ? (
              <div className="w-full flex items-center justify-center gap-2 bg-input border border-theme rounded-xl py-3 text-sm text-theme-secondary">
                <Loader2 className="h-4 w-4 animate-spin" />
                Signing in...
              </div>
            ) : (
              <GoogleSignIn onSuccess={handleGoogleSuccess} onError={() => setError('Google sign-in was cancelled or failed.')} />
            )}
          </div>

          <div className="flex items-center gap-3 my-4">
            <div className="flex-1 h-px bg-theme" />
            <span className="text-xs text-theme-tertiary">or continue with email</span>
            <div className="flex-1 h-px bg-theme" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isSignUp && (
              <div className="relative">
                <User className="absolute left-3 top-3 h-4 w-4 text-theme-tertiary" />
                <input
                  type="text"
                  placeholder="Full name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 text-sm bg-input border border-theme rounded-xl outline-none focus:border-theme-strong transition-colors duration-200 text-theme placeholder:text-theme-tertiary"
                  required
                />
              </div>
            )}
            <div className="relative">
              <Mail className="absolute left-3 top-3 h-4 w-4 text-theme-tertiary" />
              <input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-3 text-sm bg-input border border-theme rounded-xl outline-none focus:border-theme-strong transition-colors duration-200 text-theme placeholder:text-theme-tertiary"
                required
              />
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-4 w-4 text-theme-tertiary" />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-3 text-sm bg-input border border-theme rounded-xl outline-none focus:border-theme-strong transition-colors duration-200 text-theme placeholder:text-theme-tertiary"
                required
                minLength={6}
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-theme hover:opacity-90 text-white font-semibold py-3 rounded-xl disabled:opacity-40 transition-all duration-200 flex items-center justify-center gap-2"
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

          <p className="text-xs text-theme-tertiary text-center mt-6">
            {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button
              onClick={() => { setIsSignUp(!isSignUp); setError(''); }}
              className="text-theme hover:opacity-80 transition-colors duration-200"
            >
              {isSignUp ? 'Sign In' : 'Sign Up'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return <LoginForm />;
}

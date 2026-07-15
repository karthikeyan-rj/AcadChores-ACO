'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { Cpu, Mail, Lock, User, Loader2, AlertCircle } from 'lucide-react';
import { useAuth } from '@/lib/auth';

const GoogleSignIn = dynamic(() => import('./GoogleSignIn'), {
  ssr: false,
  loading: () => (
    <div className="w-[320px] h-[44px] bg-[#0D0F12] border border-white/[0.07] rounded-xl animate-pulse mx-auto" />
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
    <div className="flex h-screen w-screen overflow-hidden bg-[#08090B] text-[#F4F4F5]">
      {/* Subtle background gradient */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-[#7C3AED]/[0.04] blur-[120px]" />
      </div>

      <div className="w-full max-w-md mx-auto flex flex-col justify-center px-8 relative z-10">
        {/* Brand mark */}
        <div className="flex items-center gap-3 mb-10">
          <div className="w-12 h-12 rounded-2xl bg-[#7C3AED]/10 border border-[#7C3AED]/20 flex items-center justify-center">
            <Cpu className="text-[#7C3AED] h-6 w-6" />
          </div>
          <div>
            <h1 className="font-bold text-2xl tracking-wide text-[#F4F4F5]">ACO Operator</h1>
            <p className="text-xs text-[#71717A]">Autonomous Computer Operator v1.0</p>
          </div>
        </div>

        {/* Auth card */}
        <div className="bg-[#121419] border border-white/[0.07] rounded-[14px] p-8 shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
          <h2 className="text-xl font-bold mb-6 text-[#F4F4F5]">
            {isSignUp ? 'Create Account' : 'Sign In'}
          </h2>

          {error && (
            <div className="bg-[#F87171]/10 border border-[#F87171]/30 text-[#F87171] text-sm rounded-xl p-3 mb-4 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <div className="mb-4 flex justify-center">
            {submitting ? (
              <div className="w-full flex items-center justify-center gap-2 bg-[#0D0F12] border border-white/[0.07] rounded-xl py-3 text-sm text-[#A1A1AA]">
                <Loader2 className="h-4 w-4 animate-spin" />
                Signing in...
              </div>
            ) : (
              <GoogleSignIn onSuccess={handleGoogleSuccess} onError={() => setError('Google sign-in was cancelled or failed.')} />
            )}
          </div>

          <div className="flex items-center gap-3 my-4">
            <div className="flex-1 h-px bg-white/[0.07]" />
            <span className="text-xs text-[#71717A]">or continue with email</span>
            <div className="flex-1 h-px bg-white/[0.07]" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isSignUp && (
              <div className="relative">
                <User className="absolute left-3 top-3 h-4 w-4 text-[#71717A]" />
                <input
                  type="text"
                  placeholder="Full name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 text-sm bg-[#0D0F12] border border-white/[0.07] rounded-xl outline-none focus:border-[#7C3AED]/40 transition-colors duration-200 text-[#F4F4F5] placeholder-[#71717A]"
                  required
                />
              </div>
            )}
            <div className="relative">
              <Mail className="absolute left-3 top-3 h-4 w-4 text-[#71717A]" />
              <input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-3 text-sm bg-[#0D0F12] border border-white/[0.07] rounded-xl outline-none focus:border-[#7C3AED]/40 transition-colors duration-200 text-[#F4F4F5] placeholder-[#71717A]"
                required
              />
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-4 w-4 text-[#71717A]" />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-3 text-sm bg-[#0D0F12] border border-white/[0.07] rounded-xl outline-none focus:border-[#7C3AED]/40 transition-colors duration-200 text-[#F4F4F5] placeholder-[#71717A]"
                required
                minLength={6}
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-[#7C3AED] hover:bg-[#6D28D9] text-white font-semibold py-3 rounded-xl shadow-[0_4px_16px_rgba(124,58,237,0.25)] disabled:opacity-40 transition-all duration-200 flex items-center justify-center gap-2"
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

          <p className="text-xs text-[#71717A] text-center mt-6">
            {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button
              onClick={() => { setIsSignUp(!isSignUp); setError(''); }}
              className="text-[#7C3AED] hover:text-[#6D28D9] transition-colors duration-200"
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

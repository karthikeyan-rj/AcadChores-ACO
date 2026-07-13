import './globals.css';
import type { Metadata } from 'next';
import { AuthProvider } from '@/lib/auth';
import AppShell from '@/components/layout/AppShell';

export const metadata: Metadata = {
  title: 'ACO — Autonomous Computer Operator',
  description: 'Enterprise AI operating system automation platform.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="antialiased">
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}

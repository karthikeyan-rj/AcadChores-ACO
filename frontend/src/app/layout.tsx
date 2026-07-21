import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/lib/auth';
import { SystemHealthProvider } from '@/lib/health';
import { ThemeProvider } from '@/lib/theme';
import { ThemeScript } from '@/components/layout/ThemeScript';
import { WorkflowProvider } from '@/lib/workflow-store';

export const metadata: Metadata = {
  title: 'ACO — Autonomous Computer Operator',
  description: 'AI-powered autonomous computer operator',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body>
        <ThemeProvider>
          <AuthProvider>
            <SystemHealthProvider>
              <WorkflowProvider>
                {children}
              </WorkflowProvider>
            </SystemHealthProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

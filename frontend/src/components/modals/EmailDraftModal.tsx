'use client';

import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Mail } from 'lucide-react';

interface EmailDraft {
  type: string;
  to?: string;
  subject?: string;
  body?: string;
  message?: string;
}

interface EmailDraftModalProps {
  draft: EmailDraft | null;
  editedSubject: string;
  editedBody: string;
  onSubjectChange: (v: string) => void;
  onBodyChange: (v: string) => void;
  onConfirm: () => void;
  onReject: () => void;
}

export function EmailDraftModal({ draft, editedSubject, editedBody, onSubjectChange, onBodyChange, onConfirm, onReject }: EmailDraftModalProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);
  if (!draft || !mounted) return null;

  return createPortal(
    <AnimatePresence mode="wait">
      <motion.div
        key="email-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.12 }}
        className="fixed inset-0 z-[9999] flex items-center justify-center"
        style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
        onClick={onReject}
      >
        <motion.div
          key="email-dialog"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 6 }}
          transition={{ duration: 0.12 }}
          className="w-[460px] bg-surface border border-theme-strong rounded-xl overflow-hidden shadow-theme-lg"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-theme">
            <div className="flex items-center gap-2">
              <Mail size={16} className="text-status-info" />
              <h3 className="text-[13px] font-semibold text-theme">Review Email</h3>
            </div>
            <button onClick={onReject} className="p-1 rounded-md hover:bg-surface-hover text-theme-tertiary cursor-pointer">
              <X size={14} />
            </button>
          </div>
          <div className="px-4 py-3 space-y-3">
            {draft.to && (
              <div>
                <label className="text-[10px] font-semibold text-theme-tertiary uppercase tracking-wider">To</label>
                <p className="text-[12px] text-theme mt-0.5">{draft.to}</p>
              </div>
            )}
            <div>
              <label className="text-[10px] font-semibold text-theme-tertiary uppercase tracking-wider">Subject</label>
              <input
                type="text"
                value={editedSubject}
                onChange={(e) => onSubjectChange(e.target.value)}
                className="w-full mt-1 px-3 py-2 text-[12px] bg-input border border-theme-strong rounded-lg text-theme outline-none focus:border-theme-tertiary transition"
              />
            </div>
            <div>
              <label className="text-[10px] font-semibold text-theme-tertiary uppercase tracking-wider">Body</label>
              <textarea
                value={editedBody}
                onChange={(e) => onBodyChange(e.target.value)}
                rows={6}
                className="w-full mt-1 px-3 py-2 text-[12px] bg-input border border-theme-strong rounded-lg text-theme outline-none focus:border-theme-tertiary transition resize-none leading-relaxed"
              />
            </div>
          </div>
          <div className="flex gap-2 px-4 py-3 border-t border-theme">
            <button onClick={onReject}
              className="flex-1 text-[12px] font-semibold py-2 rounded-lg bg-surface hover:bg-surface-hover text-theme-secondary border border-theme-strong transition cursor-pointer">
              Cancel
            </button>
            <button onClick={onConfirm}
              className="flex-1 text-[12px] font-semibold py-2 rounded-lg bg-text-primary text-text-inverse border border-text-primary transition cursor-pointer hover:opacity-90">
              Send Email
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}

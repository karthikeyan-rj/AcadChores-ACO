'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, Send, X } from 'lucide-react';

interface EmailDraftModalProps {
  draft: {
    to: string;
    subject: string;
    body: string;
  } | null;
  editedSubject: string;
  editedBody: string;
  onSubjectChange: (v: string) => void;
  onBodyChange: (v: string) => void;
  onConfirm: () => void;
  onReject: () => void;
}

export function EmailDraftModal({ draft, editedSubject, editedBody, onSubjectChange, onBodyChange, onConfirm, onReject }: EmailDraftModalProps) {
  if (!draft) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-[#121419] border border-white/[0.07] rounded-lg w-full max-w-lg overflow-hidden shadow-matte-lg"
        >
          <div className="p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-[#7C3AED]/10 border border-[#7C3AED]/20 flex items-center justify-center">
                <Mail size={20} className="text-[#7C3AED]" />
              </div>
              <div>
                <h3 className="font-bold text-sm text-[#F4F4F5]">Review Email Draft</h3>
                <p className="text-[11px] text-[#A1A1AA]">AI generated the body — edit if needed, then confirm</p>
              </div>
            </div>

            <div className="bg-[#0D0F12] rounded-xl p-4 border border-white/[0.07] space-y-3 mb-5">
              <div>
                <label className="text-[10px] text-[#71717A] uppercase font-semibold tracking-wider">To</label>
                <p className="text-xs text-[#F4F4F5] font-mono bg-[#08090B] p-2 rounded border border-white/[0.07] mt-1">{draft.to}</p>
              </div>
              <div>
                <label className="text-[10px] text-[#71717A] uppercase font-semibold tracking-wider">Subject</label>
                <input
                  type="text"
                  value={editedSubject}
                  onChange={(e) => onSubjectChange(e.target.value)}
                  className="w-full text-xs text-[#F4F4F5] font-mono bg-[#08090B] p-2 rounded border border-white/[0.07] mt-1 outline-none focus:border-[#7C3AED] transition"
                />
              </div>
              <div>
                <label className="text-[10px] text-[#71717A] uppercase font-semibold tracking-wider">Body</label>
                <textarea
                  value={editedBody}
                  onChange={(e) => onBodyChange(e.target.value)}
                  rows={6}
                  className="w-full text-xs text-[#F4F4F5] font-mono bg-[#08090B] p-2 rounded border border-white/[0.07] mt-1 outline-none focus:border-[#7C3AED] transition resize-none"
                />
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={onReject}
                className="flex-1 bg-[#F87171]/10 hover:bg-[#F87171]/20 text-[#F87171] font-semibold py-2.5 px-4 rounded-lg border border-[#F87171]/20 transition text-xs cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={onConfirm}
                className="flex-1 bg-[#7C3AED] hover:bg-[#6D28D9] text-white font-semibold py-2.5 px-4 rounded-lg shadow-matte transition text-xs cursor-pointer flex items-center justify-center gap-2"
              >
                <Send size={13} />
                Send Email
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

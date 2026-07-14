'use client';

import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldAlert } from 'lucide-react';

interface PermissionModalProps {
  permission: {
    request_id: string;
    agent_name: string;
    action: string;
    details: any;
  } | null;
  onDecision: (approved: boolean) => void;
}

export function PermissionModal({ permission, onDecision }: PermissionModalProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  if (!permission || !mounted) return null;

  const detail = permission.details || {};
  const summary = detail.path || detail.file_path || detail.command || detail.url || JSON.stringify(detail).substring(0, 60);

  return createPortal(
    <AnimatePresence mode="wait">
      <motion.div
        key={permission.request_id}
        initial={{ x: 400, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 400, opacity: 0 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        className="fixed top-4 right-4 z-[9999] w-[320px]"
      >
        <div className="bg-card border border-warning/30 rounded-xl shadow-2xl shadow-black/40 overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border/50">
            <ShieldAlert size={14} className="text-warning shrink-0" />
            <span className="text-[11px] font-semibold text-foreground truncate">
              {permission.agent_name} — {permission.action}
            </span>
          </div>
          <div className="px-3 py-2">
            <p className="text-[10px] text-gray-400 truncate">{summary}</p>
          </div>
          <div className="flex gap-2 px-3 pb-2.5">
            <button
              onClick={() => onDecision(false)}
              className="flex-1 text-[11px] font-semibold py-1.5 rounded-lg bg-danger/10 hover:bg-danger/20 text-danger border border-danger/20 transition cursor-pointer"
            >
              Block
            </button>
            <button
              onClick={() => onDecision(true)}
              className="flex-1 text-[11px] font-semibold py-1.5 rounded-lg bg-primary hover:bg-primary-hover text-white shadow-lg shadow-primary/20 transition cursor-pointer"
            >
              Allow
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}

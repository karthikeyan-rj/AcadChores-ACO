'use client';

import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Check, X } from 'lucide-react';

interface PermissionModalProps {
  permission: any;
  onDecision: (approved: boolean) => void;
}

export function PermissionModal({ permission, onDecision }: PermissionModalProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);
  if (!permission || !mounted) return null;

  return createPortal(
    <AnimatePresence mode="wait">
      <motion.div
        key="perm-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.12 }}
        className="fixed inset-0 z-[9999] flex items-center justify-center"
        style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
        onClick={() => onDecision(false)}
      >
        <motion.div
          key="perm-dialog"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 6 }}
          transition={{ duration: 0.12 }}
          className="w-[380px] bg-surface border border-theme-strong rounded-xl overflow-hidden shadow-theme-lg"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center gap-2.5 px-4 py-3 border-b border-theme">
            <div className="w-8 h-8 rounded-lg bg-status-warning-soft flex items-center justify-center shrink-0">
              <Shield size={16} className="text-status-warning" />
            </div>
            <div>
              <h3 className="text-[13px] font-semibold text-theme">Permission Required</h3>
              <p className="text-[10px] text-theme-tertiary">ACO needs your approval to proceed.</p>
            </div>
          </div>
          <div className="px-4 py-3">
            <div className="p-3 rounded-lg bg-surface-2 border border-theme">
              <p className="text-[12px] font-medium text-theme">{permission.action || 'Unknown action'}</p>
              {permission.details && (
                <p className="text-[11px] text-theme-secondary mt-1 font-mono break-all">{permission.details}</p>
              )}
            </div>
          </div>
          <div className="flex gap-2 px-4 py-3 border-t border-theme">
            <button
              onClick={() => onDecision(false)}
              className="flex-1 flex items-center justify-center gap-1.5 text-[12px] font-semibold py-2 rounded-lg bg-surface hover:bg-surface-hover text-theme-secondary border border-theme-strong transition cursor-pointer"
            >
              <X size={12} /> Deny
            </button>
            <button
              onClick={() => onDecision(true)}
              className="flex-1 flex items-center justify-center gap-1.5 text-[12px] font-semibold py-2 rounded-lg bg-text-primary text-text-inverse border border-text-primary transition cursor-pointer hover:opacity-90"
            >
              <Check size={12} /> Approve
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}

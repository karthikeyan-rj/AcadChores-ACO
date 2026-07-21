'use client';

import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Trash2, AlertTriangle } from 'lucide-react';
import { formatLocalDateTime } from '@/lib/utils';

interface DeleteConfirmDialogProps {
  confirmation: {
    type: string;
    path: string;
    filename?: string;
    file_size?: number | null;
    file_mtime?: string | null;
    message?: string;
  } | null;
  onConfirm: () => void;
  onCancel: () => void;
}

function formatSize(bytes: number | null | undefined): string {
  if (bytes == null) return 'Unknown';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DeleteConfirmDialog({ confirmation, onConfirm, onCancel }: DeleteConfirmDialogProps) {
  const [mounted, setMounted] = useState(false);
  const [processing, setProcessing] = useState(false);
  const processedRef = React.useRef(false);

  useEffect(() => { setMounted(true); }, []);
  useEffect(() => {
    if (confirmation) { setProcessing(false); processedRef.current = false; }
  }, [confirmation]);

  if (!confirmation || !mounted) return null;

  const filename = confirmation.filename || confirmation.path.split(/[\\/]/).pop() || confirmation.path;

  const handleConfirm = () => {
    if (processedRef.current) return;
    processedRef.current = true;
    setProcessing(true);
    onConfirm();
  };

  const handleCancel = () => {
    if (processing) return;
    onCancel();
  };

  return createPortal(
    <AnimatePresence mode="wait">
      <motion.div
        key="delete-confirm-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.12 }}
        className="fixed inset-0 z-[9999] flex items-center justify-center"
        style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
        onClick={handleCancel}
      >
        <motion.div
          key="delete-confirm-dialog"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 6 }}
          transition={{ duration: 0.12 }}
          className="w-[400px] bg-surface border border-theme-strong rounded-xl overflow-hidden shadow-theme-lg"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center gap-2.5 px-4 py-3 border-b border-theme">
            <div className="w-8 h-8 rounded-lg bg-status-error-soft flex items-center justify-center shrink-0">
              <AlertTriangle size={16} className="text-status-error" />
            </div>
            <div>
              <h3 className="text-[13px] font-semibold text-theme">Delete file?</h3>
              <p className="text-[10px] text-theme-tertiary">This action cannot be undone.</p>
            </div>
          </div>

          <div className="px-4 py-3 space-y-2">
            <div className="p-3 rounded-lg bg-surface-2 border border-theme">
              <div className="flex items-center gap-2 mb-1">
                <Trash2 size={14} className="text-status-error shrink-0" />
                <span className="text-[12px] font-medium text-theme truncate">{filename}</span>
              </div>
              <p className="text-[11px] text-theme-secondary break-all font-mono leading-relaxed">{confirmation.path}</p>
              {confirmation.file_size != null && (
                <p className="text-[10px] text-theme-tertiary mt-1">Size: {formatSize(confirmation.file_size)}</p>
              )}
              {confirmation.file_mtime && (
                <p className="text-[10px] text-theme-tertiary mt-0.5">Modified: {formatLocalDateTime(confirmation.file_mtime)}</p>
              )}
            </div>
            {confirmation.message && (
              <p className="text-[11px] text-theme-secondary">{confirmation.message}</p>
            )}
          </div>

          <div className="flex gap-2 px-4 py-3 border-t border-theme">
            <button
              onClick={handleCancel}
              disabled={processing}
              className="flex-1 text-[12px] font-semibold py-2 rounded-lg bg-surface hover:bg-surface-hover text-theme-secondary border border-theme-strong transition cursor-pointer disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={processing}
              className="flex-1 text-[12px] font-semibold py-2 rounded-lg bg-status-error hover:opacity-90 text-white border border-status-error transition cursor-pointer flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Trash2 size={12} /> Delete file
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}

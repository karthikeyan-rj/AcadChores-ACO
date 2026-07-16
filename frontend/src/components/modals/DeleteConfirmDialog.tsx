'use client';

import React, { useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Trash2, AlertTriangle, FileX } from 'lucide-react';

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
  const processedRef = useRef(false);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    if (confirmation) {
      setProcessing(false);
      processedRef.current = false;
    }
  }, [confirmation]);

  if (!confirmation || !mounted) return null;

  const filename = confirmation.filename || confirmation.path.split(/[\\/]/).pop() || confirmation.path;
  const path = confirmation.path;

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
        transition={{ duration: 0.15 }}
        className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm"
        onClick={handleCancel}
      >
        <motion.div
          key="delete-confirm-dialog"
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          transition={{ type: 'spring', damping: 25, stiffness: 350 }}
          className="w-[380px] bg-[#121419] border border-[#F87171]/20 rounded-xl shadow-2xl overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center gap-2.5 px-4 py-3 border-b border-white/[0.07]">
            <div className="w-8 h-8 rounded-lg bg-[#F87171]/10 flex items-center justify-center shrink-0">
              <AlertTriangle size={16} className="text-[#F87171]" />
            </div>
            <div>
              <h3 className="text-[13px] font-semibold text-[#F4F4F5]">Delete file?</h3>
              <p className="text-[10px] text-[#71717A]">This action cannot be undone.</p>
            </div>
          </div>

          {/* File details */}
          <div className="px-4 py-3 space-y-2">
            <div className="flex items-start gap-2">
              <FileX size={14} className="text-[#F87171] mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="text-[12px] font-medium text-[#F4F4F5] truncate">{filename}</p>
                <p className="text-[10px] text-[#71717A] mt-0.5 break-all leading-relaxed">{path}</p>
              </div>
            </div>
            {(confirmation.file_size != null || confirmation.file_mtime) && (
              <div className="ml-5 flex gap-4 text-[10px] text-[#A1A1AA]">
                {confirmation.file_size != null && (
                  <span>Size: {formatSize(confirmation.file_size)}</span>
                )}
                {confirmation.file_mtime && (
                  <span>Modified: {confirmation.file_mtime}</span>
                )}
              </div>
            )}
          </div>

          {/* Warning */}
          <div className="mx-4 mb-3 px-3 py-2 rounded-lg bg-[#F87171]/[0.06] border border-[#F87171]/10">
            <p className="text-[10px] text-[#F87171]/80 leading-relaxed">
              The file will be permanently deleted from disk. This cannot be reversed.
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex gap-2 px-4 pb-4">
            <button
              onClick={handleCancel}
              disabled={processing}
              className="flex-1 text-[12px] font-semibold py-2 rounded-lg bg-[#1E2028] hover:bg-[#262830] text-[#A1A1AA] border border-white/[0.07] transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={processing}
              className="flex-1 text-[12px] font-semibold py-2 rounded-lg bg-[#F87171] hover:bg-[#DC2626] text-white shadow-lg transition cursor-pointer disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
            >
              {processing ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full"
                  />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 size={12} />
                  Delete file
                </>
              )}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}

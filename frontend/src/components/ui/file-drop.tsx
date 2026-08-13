"use client";
import { useId, useRef, useState, type DragEvent } from "react";

/** Mirrors `MAX_DOCUMENT_BYTES` in `backend/src/ugjcs/application/documents.py`. A
 * client-side check only supplements the server's — it saves a round trip for the common
 * mistake, it never replaces the 413/415 the backend still enforces on every upload. */
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

function validatePdf(file: File): string | null {
  const looksLikePdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!looksLikePdf) return "Only PDF files are accepted.";
  if (file.size > MAX_UPLOAD_BYTES) {
    return `That file is too large — the limit is ${MAX_UPLOAD_BYTES / (1024 * 1024)} MB.`;
  }
  return null;
}

interface PdfDropzoneProps {
  label: string;
  file: File | null;
  onSelect: (file: File | null, error: string | null) => void;
  disabled?: boolean;
}

/** A PDF file picker with drag-and-drop, used by the submission and resubmission forms.
 * Validates type and size client-side and reports the result via `onSelect` — the caller
 * owns the resulting error message and where it renders, this component only detects it. */
export function PdfDropzone({ label, file, onSelect, disabled = false }: PdfDropzoneProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function handleFiles(files: FileList | null) {
    const picked = files?.[0] ?? null;
    if (!picked) {
      onSelect(null, null);
      return;
    }
    const error = validatePdf(picked);
    onSelect(error ? null : picked, error);
  }

  return (
    <div>
      <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-ink">
        {label}
      </label>
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled || undefined}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(event) => {
          if (!disabled && (event.key === "Enter" || event.key === " ")) {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(event: DragEvent<HTMLDivElement>) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event: DragEvent<HTMLDivElement>) => {
          event.preventDefault();
          setDragging(false);
          if (!disabled) handleFiles(event.dataTransfer.files);
        }}
        className={`flex flex-col items-center justify-center gap-1 rounded-[3px] border border-dashed px-4 py-6 text-center text-sm transition-colors
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stamp
          ${dragging ? "border-stamp bg-stamp/5" : "border-rule bg-white"}
          ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:border-stamp/60"}`}
      >
        <span className="text-ink/70">{file ? file.name : "Drag a PDF here, or click to browse"}</span>
        {file && <span className="text-xs text-ink/50">{(file.size / (1024 * 1024)).toFixed(2)} MB</span>}
      </div>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept="application/pdf,.pdf"
        disabled={disabled}
        className="sr-only"
        onChange={(event) => handleFiles(event.target.files)}
      />
    </div>
  );
}

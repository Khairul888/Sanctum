import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Paperclip, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { attachFile, type Attachment } from "@/api/sanctum";
import { useSettingsStore } from "@/store";

const ACCEPTED_EXTENSIONS = ".txt,.pdf,.jpg,.jpeg,.png";
const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024;

interface MessageInputProps {
  onSend: (message: string, attachment?: Attachment) => void;
  disabled?: boolean;
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [value, setValue] = useState("");
  const [pendingFilename, setPendingFilename] = useState<string | null>(null);
  const [attachment, setAttachment] = useState<Attachment | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { gatewayUrl, apiKey } = useSettingsStore();

  const attachMutation = useMutation({
    mutationFn: (file: File) => attachFile(file, { gatewayUrl, apiKey }),
    onSuccess: (data) => {
      setAttachment(data);
      setAttachError(null);
    },
    onError: (err) => {
      setAttachError(err instanceof Error ? err.message : "Failed to process attachment");
      setPendingFilename(null);
    },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (file.size > MAX_ATTACHMENT_BYTES) {
      setAttachError("File is too large (max 10MB)");
      return;
    }
    setAttachError(null);
    setAttachment(null);
    setPendingFilename(file.name);
    attachMutation.mutate(file);
  }

  function removeAttachment() {
    setPendingFilename(null);
    setAttachment(null);
    setAttachError(null);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!value.trim() || attachMutation.isPending) return;
    onSend(value, attachment ?? undefined);
    setValue("");
    removeAttachment();
  }

  const isBusy = disabled || attachMutation.isPending;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2 border-t p-4">
      {(pendingFilename || attachError) && (
        <div className="flex items-center gap-2 text-sm">
          {attachError ? (
            <span className="text-destructive">{attachError}</span>
          ) : (
            <span className="flex items-center gap-1 rounded-md border bg-muted px-2 py-1">
              {attachMutation.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Paperclip className="h-3 w-3" />
              )}
              {pendingFilename}
              <button type="button" onClick={removeAttachment} aria-label="Remove attachment">
                <X className="h-3 w-3" />
              </button>
            </span>
          )}
        </div>
      )}
      <div className="flex gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS}
          className="hidden"
          onChange={handleFileChange}
        />
        <input
          className="flex-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring"
          placeholder="Ask Sanctum..."
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          disabled={isBusy}
          onClick={() => fileInputRef.current?.click()}
          aria-label="Attach file"
        >
          <Paperclip className="h-4 w-4" />
        </Button>
        <Button type="submit" disabled={isBusy}>
          Send
        </Button>
      </div>
    </form>
  );
}

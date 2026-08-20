import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { RotateCcw, Cpu } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";
import { query, resetMemory, type Attachment } from "@/api/sanctum";
import { useSettingsStore } from "@/store";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
  attachmentName?: string;
}

export function ChatScreen() {
  const { gatewayUrl, apiKey } = useSettingsStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const sendMutation = useMutation({
    mutationFn: ({ prompt, attachment }: { prompt: string; attachment?: Attachment }) =>
      query(prompt, { gatewayUrl, apiKey }, attachment),
  });

  const clearMutation = useMutation({
    mutationFn: () => resetMemory({ gatewayUrl, apiKey }),
    onSuccess: () => setMessages([]),
  });

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sendMutation.isPending]);

  function handleSend(content: string, attachment?: Attachment) {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      attachmentName: attachment?.filename,
    };
    setMessages((prev) => [...prev, userMessage]);

    sendMutation.mutate(
      { prompt: content, attachment },
      {
        onSuccess: (data) => {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: data.answer,
              toolsUsed: data.tools_used,
            },
          ]);
        },
      },
    );
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Cpu className="h-4 w-4" />
          <span>Ollama</span>
        </div>
        <button
          onClick={() => clearMutation.mutate()}
          disabled={messages.length === 0 || clearMutation.isPending}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-muted disabled:opacity-40"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Clear conversation
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto flex max-w-3xl flex-col gap-3">
          {messages.length === 0 && (
            <p className="mt-10 text-center text-sm text-muted-foreground">
              Ask Sanctum a question to get started.
            </p>
          )}
          {messages.map((m) => (
            <MessageBubble
              key={m.id}
              role={m.role}
              content={m.content}
              toolsUsed={m.toolsUsed}
              attachmentName={m.attachmentName}
            />
          ))}
          {sendMutation.isPending && (
            <MessageBubble role="assistant" content="Thinking…" />
          )}
          {sendMutation.isError && (
            <p className="text-sm text-destructive">
              Failed to reach the gateway. Check your gateway URL and API key in
              Settings.
            </p>
          )}
          <div ref={scrollRef} />
        </div>
      </div>

      <div className="mx-auto w-full max-w-3xl">
        <MessageInput onSend={handleSend} disabled={sendMutation.isPending} />
      </div>
    </div>
  );
}

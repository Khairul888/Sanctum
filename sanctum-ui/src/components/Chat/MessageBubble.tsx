import { BookOpen, Globe, Paperclip } from "lucide-react";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
  attachmentName?: string;
}

const TOOL_LABELS: Record<string, { label: string; icon: typeof BookOpen }> = {
  rag_search: { label: "RAG", icon: BookOpen },
  web_search: { label: "Web Search", icon: Globe },
};

export function MessageBubble({ role, content, toolsUsed, attachmentName }: MessageBubbleProps) {
  const isUser = role === "user";
  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      {isUser && attachmentName && (
        <span className="mb-1 flex items-center gap-1 text-xs text-muted-foreground">
          <Paperclip className="h-3 w-3" />
          {attachmentName}
        </span>
      )}
      {!!toolsUsed?.length && (
        <div className="mb-1 flex gap-1.5">
          {toolsUsed.map((tool, i) => {
            const meta = TOOL_LABELS[tool] ?? { label: tool, icon: BookOpen };
            const Icon = meta.icon;
            return (
              <span
                key={`${tool}-${i}`}
                className="flex items-center gap-1 rounded-full border bg-muted px-2 py-0.5 text-xs text-muted-foreground"
              >
                <Icon className="h-3 w-3" />
                {meta.label}
              </span>
            );
          })}
        </div>
      )}
      <div
        className={`max-w-[75%] rounded-lg px-4 py-2 ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground font-mono"
        }`}
      >
        {content}
      </div>
    </div>
  );
}

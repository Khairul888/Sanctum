import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { FileUpload } from "./FileUpload";
import { ingest } from "@/api/sanctum";
import { useSettingsStore } from "@/store";

export function DocumentsScreen() {
  const config = useSettingsStore();

  const [uploadStatus, setUploadStatus] = useState<Record<string, "pending" | "done" | "error">>({});

  const ingestMutation = useMutation({
    mutationFn: (file: File) => ingest(file, config),
  });

  function handleFilesSelected(files: FileList) {
    Array.from(files).forEach((file) => {
      setUploadStatus((s) => ({ ...s, [file.name]: "pending" }));
      ingestMutation.mutate(file, {
        onSuccess: () => setUploadStatus((s) => ({ ...s, [file.name]: "done" })),
        onError: () => setUploadStatus((s) => ({ ...s, [file.name]: "error" })),
      });
    });
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-6">
      <h2 className="text-sm font-medium text-muted-foreground">Documents</h2>
      <FileUpload onFilesSelected={handleFilesSelected} />
      {Object.keys(uploadStatus).length > 0 && (
        <ul className="space-y-1 text-sm">
          {Object.entries(uploadStatus).map(([name, status]) => (
            <li key={name} className="flex items-center gap-2 text-muted-foreground">
              <FileText className="h-3.5 w-3.5" />
              <span>{name}</span>
              <span
                className={
                  status === "done"
                    ? "text-green-500"
                    : status === "error"
                      ? "text-destructive"
                      : ""
                }
              >
                {status === "pending" ? "Uploading…" : status === "done" ? "Ingested" : "Failed"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

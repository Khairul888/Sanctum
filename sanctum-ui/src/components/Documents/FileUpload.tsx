interface FileUploadProps {
  onFilesSelected: (files: FileList) => void;
}

export function FileUpload({ onFilesSelected }: FileUploadProps) {
  return (
    <div
      className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 text-sm text-muted-foreground"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length) onFilesSelected(e.dataTransfer.files);
      }}
    >
      <p>Drag and drop PDF, TXT, JPG, or PNG files here</p>
      <input
        type="file"
        multiple
        accept=".pdf,.txt,.jpg,.jpeg,.png"
        className="mt-4 text-xs"
        onChange={(e) => {
          if (e.target.files?.length) onFilesSelected(e.target.files);
        }}
      />
    </div>
  );
}

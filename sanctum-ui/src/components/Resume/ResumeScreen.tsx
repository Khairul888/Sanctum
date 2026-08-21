import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  getProfile,
  uploadResume,
  updateProfile,
  type Profile,
} from "@/api/sanctum";
import { useSettingsStore } from "@/store";

const EMPTY_PROFILE: Profile = {
  name: "",
  email: "",
  phone: "",
  location: "",
  summary: "",
  skills: [],
  work_history: [],
  education: [],
};

const inputClass =
  "w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring";

export function ResumeScreen() {
  const config = useSettingsStore();
  const queryClient = useQueryClient();

  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);

  const profileQuery = useQuery({
    queryKey: ["profile"],
    queryFn: () => getProfile(config),
    retry: false,
  });

  useEffect(() => {
    if (profileQuery.data) setProfile(profileQuery.data);
  }, [profileQuery.data]);

  const resumeMutation = useMutation({
    mutationFn: (file: File) => uploadResume(file, config),
    onSuccess: (data) => {
      setProfile(data);
      queryClient.setQueryData(["profile"], data);
    },
  });

  const saveMutation = useMutation({
    mutationFn: () => updateProfile(profile, config),
  });

  function handleResumeSelected(files: FileList) {
    const file = files[0];
    if (file) resumeMutation.mutate(file);
  }

  function updateWorkHistory(index: number, key: keyof Profile["work_history"][number], value: string) {
    setProfile((p) => ({
      ...p,
      work_history: p.work_history.map((entry, i) => (i === index ? { ...entry, [key]: value } : entry)),
    }));
  }

  function updateEducation(index: number, key: keyof Profile["education"][number], value: string) {
    setProfile((p) => ({
      ...p,
      education: p.education.map((entry, i) => (i === index ? { ...entry, [key]: value } : entry)),
    }));
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-muted-foreground">Resume / Profile</h2>
        {profileQuery.isLoading && (
          <span className="text-xs text-muted-foreground">Loading…</span>
        )}
      </div>

      <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-sm text-muted-foreground hover:bg-muted">
        <UploadCloud className="h-4 w-4" />
        {resumeMutation.isPending ? "Extracting profile…" : "Upload resume (PDF, DOCX, TXT)"}
        <input
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={(e) => e.target.files && handleResumeSelected(e.target.files)}
        />
      </label>
      {resumeMutation.isError && (
        <p className="text-sm text-destructive">Failed to extract a profile from that resume.</p>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label className="text-sm">Name</label>
          <input
            className={inputClass}
            value={profile.name}
            onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm">Email</label>
          <input
            className={inputClass}
            value={profile.email}
            onChange={(e) => setProfile((p) => ({ ...p, email: e.target.value }))}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm">Phone</label>
          <input
            className={inputClass}
            value={profile.phone}
            onChange={(e) => setProfile((p) => ({ ...p, phone: e.target.value }))}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm">Location</label>
          <input
            className={inputClass}
            value={profile.location}
            onChange={(e) => setProfile((p) => ({ ...p, location: e.target.value }))}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="text-sm">Summary</label>
        <textarea
          className={inputClass}
          rows={3}
          value={profile.summary}
          onChange={(e) => setProfile((p) => ({ ...p, summary: e.target.value }))}
        />
      </div>

      <div className="space-y-1.5">
        <label className="text-sm">Skills (comma separated)</label>
        <input
          className={inputClass}
          value={profile.skills.join(", ")}
          onChange={(e) =>
            setProfile((p) => ({
              ...p,
              skills: e.target.value
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
            }))
          }
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm">Work history</label>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              setProfile((p) => ({
                ...p,
                work_history: [
                  ...p.work_history,
                  { company: "", title: "", start_date: "", end_date: "", description: "" },
                ],
              }))
            }
          >
            <Plus className="h-3.5 w-3.5" />
            Add entry
          </Button>
        </div>
        {profile.work_history.map((entry, i) => (
          <div key={i} className="space-y-2 rounded-md border p-3">
            <div className="grid grid-cols-2 gap-2">
              <input
                className={inputClass}
                placeholder="Company"
                value={entry.company}
                onChange={(e) => updateWorkHistory(i, "company", e.target.value)}
              />
              <input
                className={inputClass}
                placeholder="Title"
                value={entry.title}
                onChange={(e) => updateWorkHistory(i, "title", e.target.value)}
              />
              <input
                className={inputClass}
                placeholder="Start date"
                value={entry.start_date}
                onChange={(e) => updateWorkHistory(i, "start_date", e.target.value)}
              />
              <input
                className={inputClass}
                placeholder="End date"
                value={entry.end_date}
                onChange={(e) => updateWorkHistory(i, "end_date", e.target.value)}
              />
            </div>
            <textarea
              className={inputClass}
              rows={2}
              placeholder="Description"
              value={entry.description}
              onChange={(e) => updateWorkHistory(i, "description", e.target.value)}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setProfile((p) => ({
                  ...p,
                  work_history: p.work_history.filter((_, idx) => idx !== i),
                }))
              }
            >
              <Trash2 className="h-3.5 w-3.5" />
              Remove
            </Button>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm">Education</label>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              setProfile((p) => ({
                ...p,
                education: [...p.education, { institution: "", degree: "", field: "", year: "" }],
              }))
            }
          >
            <Plus className="h-3.5 w-3.5" />
            Add entry
          </Button>
        </div>
        {profile.education.map((entry, i) => (
          <div key={i} className="space-y-2 rounded-md border p-3">
            <div className="grid grid-cols-2 gap-2">
              <input
                className={inputClass}
                placeholder="Institution"
                value={entry.institution}
                onChange={(e) => updateEducation(i, "institution", e.target.value)}
              />
              <input
                className={inputClass}
                placeholder="Degree"
                value={entry.degree}
                onChange={(e) => updateEducation(i, "degree", e.target.value)}
              />
              <input
                className={inputClass}
                placeholder="Field"
                value={entry.field}
                onChange={(e) => updateEducation(i, "field", e.target.value)}
              />
              <input
                className={inputClass}
                placeholder="Year"
                value={entry.year}
                onChange={(e) => updateEducation(i, "year", e.target.value)}
              />
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setProfile((p) => ({
                  ...p,
                  education: p.education.filter((_, idx) => idx !== i),
                }))
              }
            >
              <Trash2 className="h-3.5 w-3.5" />
              Remove
            </Button>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? "Saving…" : "Save profile"}
        </Button>
        {saveMutation.isSuccess && (
          <span className="text-sm text-green-500">Saved</span>
        )}
        {saveMutation.isError && (
          <span className="text-sm text-destructive">Failed to save</span>
        )}
      </div>
    </div>
  );
}

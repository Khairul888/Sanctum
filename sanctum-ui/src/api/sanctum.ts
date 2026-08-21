import axios from "axios";

export interface SanctumConfig {
  gatewayUrl: string;
  apiKey: string;
}

function client({ gatewayUrl, apiKey }: SanctumConfig) {
  return axios.create({
    baseURL: gatewayUrl,
    headers: apiKey ? { "x-api-key": apiKey } : undefined,
  });
}

export interface Attachment {
  filename: string;
  text: string;
}

export async function query(
  prompt: string,
  config: SanctumConfig,
  attachment?: Attachment,
) {
  const { data } = await client(config).post<{
    answer: string;
    tools_used: string[];
  }>("/query/agent", { prompt, attachment });
  return data;
}

export async function attachFile(file: File, config: SanctumConfig) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client(config).post<Attachment>("/attach", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function resetMemory(config: SanctumConfig) {
  const { data } = await client(config).post("/memory/reset");
  return data;
}

export async function ingest(file: File, config: SanctumConfig) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client(config).post("/ingest", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export interface WorkHistoryEntry {
  company: string;
  title: string;
  start_date: string;
  end_date: string;
  description: string;
}

export interface EducationEntry {
  institution: string;
  degree: string;
  field: string;
  year: string;
}

export interface Profile {
  name: string;
  email: string;
  phone: string;
  location: string;
  summary: string;
  skills: string[];
  work_history: WorkHistoryEntry[];
  education: EducationEntry[];
}

export async function uploadResume(file: File, config: SanctumConfig) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client(config).post<Profile>("/profile/resume", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getProfile(config: SanctumConfig) {
  const { data } = await client(config).get<Profile>("/profile");
  return data;
}

export async function updateProfile(profile: Profile, config: SanctumConfig) {
  const { data } = await client(config).put<Profile>("/profile", profile);
  return data;
}

export async function getStatus(config: SanctumConfig) {
  const { data } = await client(config).get("/health/detailed");
  return data;
}

export async function ping(config: SanctumConfig) {
  const { data } = await client(config).get<{ message: string }>("/");
  return data;
}

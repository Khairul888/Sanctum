import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark";

interface SanctumSettings {
  gatewayUrl: string;
  apiKey: string;
  theme: Theme;
  setGatewayUrl: (url: string) => void;
  setApiKey: (key: string) => void;
  setTheme: (theme: Theme) => void;
}

export const useSettingsStore = create<SanctumSettings>()(
  persist(
    (set) => ({
      gatewayUrl: "http://localhost:8080",
      apiKey: "",
      theme: "dark",
      setGatewayUrl: (gatewayUrl) => set({ gatewayUrl }),
      setApiKey: (apiKey) => set({ apiKey }),
      setTheme: (theme) => set({ theme }),
    }),
    { name: "sanctum-settings" },
  ),
);

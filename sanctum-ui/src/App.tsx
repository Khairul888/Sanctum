import { useState } from "react";
import { ChatScreen } from "@/components/Chat/ChatScreen";
import { DocumentsScreen } from "@/components/Documents/DocumentsScreen";
import { ResumeScreen } from "@/components/Resume/ResumeScreen";
import { SettingsScreen } from "@/components/Settings/SettingsScreen";
import { StatusScreen } from "@/components/Status/StatusScreen";
import { useSettingsStore } from "@/store";
import "./App.css";

const SCREENS = {
  chat: { label: "Chat", component: ChatScreen },
  documents: { label: "Documents", component: DocumentsScreen },
  resume: { label: "Resume", component: ResumeScreen },
  settings: { label: "Settings", component: SettingsScreen },
  status: { label: "Status", component: StatusScreen },
} as const;

type ScreenKey = keyof typeof SCREENS;

function App() {
  const [screen, setScreen] = useState<ScreenKey>("chat");
  const theme = useSettingsStore((s) => s.theme);
  const Screen = SCREENS[screen].component;

  return (
    <div
      className={`${theme} flex h-screen w-screen bg-background text-foreground`}
    >
      <nav className="flex w-48 flex-col border-r p-2">
        {(Object.keys(SCREENS) as ScreenKey[]).map((key) => (
          <button
            key={key}
            onClick={() => setScreen(key)}
            className={`rounded-md px-3 py-2 text-left text-sm ${
              screen === key
                ? "bg-primary text-primary-foreground"
                : "hover:bg-muted"
            }`}
          >
            {SCREENS[key].label}
          </button>
        ))}
      </nav>
      <main className="flex-1 overflow-auto">
        <Screen />
      </main>
    </div>
  );
}

export default App;

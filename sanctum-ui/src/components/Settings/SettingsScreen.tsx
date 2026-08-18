import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, XCircle, Eye, EyeOff, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ping } from "@/api/sanctum";
import { useSettingsStore } from "@/store";

export function SettingsScreen() {
  const { gatewayUrl, apiKey, theme, setGatewayUrl, setApiKey, setTheme } =
    useSettingsStore();
  const [showApiKey, setShowApiKey] = useState(false);

  const testConnection = useMutation({
    mutationFn: () => ping({ gatewayUrl, apiKey }),
  });

  return (
    <div className="mx-auto max-w-xl space-y-8 p-6">
      <section className="space-y-4">
        <h2 className="text-sm font-medium text-muted-foreground">Gateway</h2>

        <div className="space-y-1.5">
          <label className="text-sm">Gateway URL</label>
          <input
            className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring"
            value={gatewayUrl}
            onChange={(e) => setGatewayUrl(e.target.value)}
            placeholder="http://localhost:8080"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-sm">API key</label>
          <div className="relative">
            <input
              type={showApiKey ? "text" : "password"}
              className="w-full rounded-md border bg-background px-3 py-2 pr-9 text-sm outline-none focus:ring-1 focus:ring-ring"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter your Sanctum API key"
            />
            <button
              type="button"
              onClick={() => setShowApiKey((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground"
            >
              {showApiKey ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => testConnection.mutate()}
            disabled={testConnection.isPending}
          >
            {testConnection.isPending ? "Testing…" : "Test connection"}
          </Button>
          {testConnection.isSuccess && (
            <span className="flex items-center gap-1.5 text-sm text-green-500">
              <CheckCircle2 className="h-4 w-4" />
              Gateway reachable
            </span>
          )}
          {testConnection.isError && (
            <span className="flex items-center gap-1.5 text-sm text-destructive">
              <XCircle className="h-4 w-4" />
              Could not reach gateway
            </span>
          )}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-medium text-muted-foreground">Model</h2>
        <div className="space-y-1.5">
          <label className="text-sm">Active model</label>
          <select
            disabled
            className="w-full rounded-md border bg-background px-3 py-2 text-sm text-muted-foreground outline-none"
          >
            <option>Model selection requires GET /models on the gateway</option>
          </select>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-medium text-muted-foreground">Appearance</h2>
        <div className="flex gap-2">
          <Button
            variant={theme === "dark" ? "default" : "outline"}
            onClick={() => setTheme("dark")}
            className="gap-2"
          >
            <Moon className="h-4 w-4" />
            Dark
          </Button>
          <Button
            variant={theme === "light" ? "default" : "outline"}
            onClick={() => setTheme("light")}
            className="gap-2"
          >
            <Sun className="h-4 w-4" />
            Light
          </Button>
        </div>
      </section>
    </div>
  );
}

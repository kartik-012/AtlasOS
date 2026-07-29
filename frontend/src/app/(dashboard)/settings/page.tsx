"use client";

import { useState } from "react";
import {
  Settings,
  Key,
  Bell,
  Shield,
  Copy,
  Eye,
  EyeOff,
  RefreshCw,
  Trash2,
  Save,
  Check,
} from "lucide-react";
import { motion } from "framer-motion";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

/* ─── Toggle Switch ─── */

function Toggle({
  checked,
  onChange,
  id,
}: {
  checked: boolean;
  onChange: (val: boolean) => void;
  id: string;
}) {
  return (
    <button
      id={id}
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
        checked ? "bg-primary" : "bg-muted"
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition-transform duration-200 ease-in-out ${
          checked ? "translate-x-5" : "translate-x-0"
        }`}
      />
    </button>
  );
}

/* ─── Section Wrapper ─── */

function SettingsSection({
  icon: Icon,
  title,
  description,
  gradient,
  index,
  children,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  gradient: string;
  index: number;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1, ease: "easeOut" }}
    >
      <Card className="glass-card">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div
              className={`h-9 w-9 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg`}
            >
              <Icon className="h-4.5 w-4.5 text-white" />
            </div>
            <div>
              <CardTitle className="text-base">{title}</CardTitle>
              <CardDescription className="text-xs mt-0.5">
                {description}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </motion.div>
  );
}

/* ─── Settings Page ─── */

export default function SettingsPage() {
  const [instanceName, setInstanceName] = useState("production-01");
  const [maxMemories, setMaxMemories] = useState("100000");
  const [compressionThreshold, setCompressionThreshold] = useState("0.85");
  const [apiKeyVisible, setApiKeyVisible] = useState(false);
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);

  // Notification toggles
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [contradictionAlerts, setContradictionAlerts] = useState(true);
  const [tenantAlerts, setTenantAlerts] = useState(false);
  const [weeklyDigest, setWeeklyDigest] = useState(true);

  const mockApiKey = "atlas_sk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6";

  const handleCopyKey = () => {
    navigator.clipboard.writeText(mockApiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Page header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Configure your AtlasOS instance and manage API access.
        </p>
      </motion.div>

      {/* General Settings */}
      <SettingsSection
        icon={Settings}
        title="General"
        description="Core instance configuration"
        gradient="from-gray-400 to-gray-500"
        index={0}
      >
        <div className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="instance-name" className="text-sm text-foreground">
                Instance Name
              </Label>
              <Input
                id="instance-name"
                value={instanceName}
                onChange={(e) => setInstanceName(e.target.value)}
                className="bg-background/50 border-border h-10"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="max-memories" className="text-sm text-foreground">
                Max Memories per Tenant
              </Label>
              <Input
                id="max-memories"
                type="number"
                value={maxMemories}
                onChange={(e) => setMaxMemories(e.target.value)}
                className="bg-background/50 border-border h-10"
              />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label
                htmlFor="compression-threshold"
                className="text-sm text-foreground"
              >
                Compression Similarity Threshold
              </Label>
              <Input
                id="compression-threshold"
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={compressionThreshold}
                onChange={(e) => setCompressionThreshold(e.target.value)}
                className="bg-background/50 border-border h-10"
              />
              <p className="text-xs text-muted-foreground">
                Memories above this cosine similarity are compressed together.
              </p>
            </div>
          </div>
        </div>
      </SettingsSection>

      {/* API Keys */}
      <SettingsSection
        icon={Key}
        title="API Keys"
        description="Manage your API access credentials"
        gradient="from-violet-500 to-purple-600"
        index={1}
      >
        <div className="space-y-4">
          <div className="space-y-2">
            <Label className="text-sm text-foreground">Primary API Key</Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  id="api-key-display"
                  value={
                    apiKeyVisible
                      ? mockApiKey
                      : "atlas_sk_••••••••••••••••••••••••••••"
                  }
                  readOnly
                  className="bg-background/50 border-border h-10 font-mono text-sm pr-10"
                />
                <button
                  id="toggle-api-key-visibility"
                  onClick={() => setApiKeyVisible(!apiKeyVisible)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {apiKeyVisible ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              <Button
                id="copy-api-key"
                variant="outline"
                size="icon"
                className="h-10 w-10 border-border hover:bg-secondary"
                onClick={handleCopyKey}
              >
                {copied ? (
                  <Check className="h-4 w-4 text-emerald-400" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
              <Button
                id="regenerate-api-key"
                variant="outline"
                className="h-10 border-border hover:bg-secondary gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Regenerate
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Created on Jan 12, 2025 · Last used 3 minutes ago
            </p>
          </div>
        </div>
      </SettingsSection>

      {/* Notifications */}
      <SettingsSection
        icon={Bell}
        title="Notifications"
        description="Configure alert preferences"
        gradient="from-amber-500 to-orange-600"
        index={2}
      >
        <div className="space-y-4">
          {[
            {
              id: "email-alerts",
              label: "Email Alerts",
              desc: "Receive critical system alerts via email",
              checked: emailAlerts,
              onChange: setEmailAlerts,
            },
            {
              id: "contradiction-alerts",
              label: "Contradiction Detections",
              desc: "Alert when memory contradictions are found",
              checked: contradictionAlerts,
              onChange: setContradictionAlerts,
            },
            {
              id: "tenant-alerts",
              label: "Tenant Activity",
              desc: "Notify on new tenant provisioning and deletions",
              checked: tenantAlerts,
              onChange: setTenantAlerts,
            },
            {
              id: "weekly-digest",
              label: "Weekly Digest",
              desc: "Summary of key metrics delivered every Monday",
              checked: weeklyDigest,
              onChange: setWeeklyDigest,
            },
          ].map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between py-2 px-1"
            >
              <div>
                <p className="text-sm font-medium text-foreground">
                  {item.label}
                </p>
                <p className="text-xs text-muted-foreground">{item.desc}</p>
              </div>
              <Toggle
                id={item.id}
                checked={item.checked}
                onChange={item.onChange}
              />
            </div>
          ))}
        </div>
      </SettingsSection>

      {/* Danger Zone */}
      <SettingsSection
        icon={Shield}
        title="Danger Zone"
        description="Destructive actions — proceed with caution"
        gradient="from-red-500 to-rose-600"
        index={3}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between py-2 px-1 rounded-lg">
            <div>
              <p className="text-sm font-medium text-foreground">
                Purge All Memories
              </p>
              <p className="text-xs text-muted-foreground">
                Permanently delete all memories across every tenant. This cannot
                be undone.
              </p>
            </div>
            <Button
              id="purge-memories-btn"
              variant="outline"
              className="border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300 gap-2"
            >
              <Trash2 className="h-4 w-4" />
              Purge
            </Button>
          </div>
          <div className="flex items-center justify-between py-2 px-1 rounded-lg">
            <div>
              <p className="text-sm font-medium text-zinc-200">
                Reset Instance
              </p>
              <p className="text-xs text-muted-foreground">
                Reset all configuration to defaults and remove all tenants.
              </p>
            </div>
            <Button
              id="reset-instance-btn"
              variant="outline"
              className="border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300 gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Reset
            </Button>
          </div>
        </div>
      </SettingsSection>

      {/* Save button */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
        className="flex justify-end pb-8"
      >
        <Button
          id="save-settings-btn"
          onClick={handleSave}
          className="h-10 px-8 gap-2"
        >
          {saved ? (
            <>
              <Check className="h-4 w-4" />
              Saved
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Save Changes
            </>
          )}
        </Button>
      </motion.div>
    </div>
  );
}

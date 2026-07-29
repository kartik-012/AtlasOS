"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { Search, LayoutDashboard, Users, Database, Key, X, Activity, Cpu, AlertTriangle, BarChart3, Globe, ScrollText, Settings } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export function CommandMenu() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    const handleCustomOpen = () => setOpen(true);

    document.addEventListener("keydown", down);
    document.addEventListener("open-command-menu", handleCustomOpen);
    return () => {
      document.removeEventListener("keydown", down);
      document.removeEventListener("open-command-menu", handleCustomOpen);
    };
  }, []);

  const runCommand = (path: string) => {
    setOpen(false);
    router.push(path);
  };

  const navItems = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, color: "text-primary" },
    { label: "Analytics", href: "/analytics", icon: Activity, color: "text-blue-500" },
    { label: "Tenants", href: "/tenants", icon: Users, color: "text-violet-500" },
    { label: "Memory Explorer", href: "/memories", icon: Database, color: "text-emerald-500" },
    { label: "Working Memory", href: "/working-memory", icon: Cpu, color: "text-cyan-500" },
    { label: "API Keys", href: "/api-keys", icon: Key, color: "text-amber-500" },
    { label: "Contradictions", href: "/contradictions", icon: AlertTriangle, color: "text-red-500" },
    { label: "Evaluations", href: "/evaluations", icon: BarChart3, color: "text-indigo-500" },
    { label: "Webhooks", href: "/webhooks", icon: Globe, color: "text-teal-500" },
    { label: "Audit Log", href: "/audit", icon: ScrollText, color: "text-slate-400" },
    { label: "Settings", href: "/settings", icon: Settings, color: "text-gray-400" },
  ];

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="fixed left-[50%] top-[15%] z-50 w-full max-w-2xl -translate-x-1/2 p-4"
          >
            <div className="glass-card overflow-hidden rounded-xl shadow-2xl border bg-card text-foreground">
              <Command
                className="flex w-full flex-col bg-transparent"
                onKeyDown={(e) => {
                  if (e.key === "Escape") setOpen(false);
                }}
              >
                <div className="flex items-center border-b border-border px-4">
                  <Search className="mr-2 h-5 w-5 text-muted-foreground" />
                  <Command.Input
                    autoFocus
                    placeholder="Search all sections, settings, memories..."
                    className="flex h-14 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 text-foreground"
                  />
                  <button onClick={() => setOpen(false)} className="ml-2 text-muted-foreground hover:text-foreground">
                    <X className="h-5 w-5" />
                  </button>
                </div>
                
                <Command.List className="max-h-[350px] overflow-y-auto overflow-x-hidden p-2">
                  <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
                    No results found.
                  </Command.Empty>
                  
                  <Command.Group heading="Navigation" className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                    {navItems.map((item) => (
                      <Command.Item
                        key={item.href}
                        onSelect={() => runCommand(item.href)}
                        className="relative flex cursor-pointer select-none items-center rounded-lg px-3 py-2.5 text-sm outline-none aria-selected:bg-secondary aria-selected:text-foreground hover:bg-secondary transition-colors my-0.5"
                      >
                        <item.icon className={`mr-3 h-4 w-4 ${item.color}`} />
                        <span>{item.label}</span>
                      </Command.Item>
                    ))}
                  </Command.Group>
                </Command.List>
              </Command>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

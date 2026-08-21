"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  LayoutDashboard,
  Users,
  Database,
  Key,
  X,
  Activity,
  Cpu,
  AlertTriangle,
  BarChart3,
  Globe,
  ScrollText,
  Settings,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export function CommandMenu() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const router = useRouter();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setOpen(false);
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

  const filteredItems = useMemo(() => {
    if (!query.trim()) return navItems;
    const lower = query.toLowerCase();
    return navItems.filter(
      (item) => item.label.toLowerCase().includes(lower) || item.href.toLowerCase().includes(lower)
    );
  }, [query, navItems]);

  const runCommand = (path: string) => {
    setOpen(false);
    setQuery("");
    router.push(path);
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="fixed left-[50%] top-[15%] z-50 w-full max-w-2xl -translate-x-1/2 p-4"
          >
            <div className="glass-card overflow-hidden rounded-xl shadow-2xl border border-border bg-card text-foreground">
              <div className="flex items-center border-b border-border px-4">
                <Search className="mr-2 h-5 w-5 text-muted-foreground" />
                <input
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search all sections, settings, memories..."
                  className="flex h-14 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground text-foreground"
                />
                <button
                  onClick={() => setOpen(false)}
                  className="ml-2 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="max-h-[350px] overflow-y-auto overflow-x-hidden p-2">
                {filteredItems.length === 0 ? (
                  <div className="py-6 text-center text-sm text-muted-foreground">
                    No results found for &ldquo;{query}&rdquo;
                  </div>
                ) : (
                  <div>
                    <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                      Navigation
                    </div>
                    {filteredItems.map((item) => (
                      <button
                        key={item.href}
                        onClick={() => runCommand(item.href)}
                        className="w-full relative flex cursor-pointer select-none items-center rounded-lg px-3 py-2.5 text-sm outline-none hover:bg-secondary transition-colors my-0.5 text-left text-foreground"
                      >
                        <item.icon className={`mr-3 h-4 w-4 ${item.color}`} />
                        <span>{item.label}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

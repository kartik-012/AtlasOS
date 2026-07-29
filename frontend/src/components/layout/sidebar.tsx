"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Database,
  Cpu,
  Key,
  AlertTriangle,
  BarChart3,
  Globe,
  ScrollText,
  Settings,
  LogOut,
  X,
  Zap,
  Activity,
} from "lucide-react";
import Cookies from "js-cookie";
import { motion, AnimatePresence } from "framer-motion";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const routes = [
  {
    label: "Dashboard",
    icon: LayoutDashboard,
    href: "/dashboard",
    gradient: "from-sky-500 to-blue-600",
  },
  {
    label: "Analytics",
    icon: Activity,
    href: "/analytics",
    gradient: "from-blue-500 to-indigo-600",
  },
  {
    label: "Tenants",
    icon: Users,
    href: "/tenants",
    gradient: "from-violet-500 to-purple-600",
  },
  {
    label: "Memory Explorer",
    icon: Database,
    href: "/memories",
    gradient: "from-emerald-500 to-teal-600",
  },
  {
    label: "Working Memory",
    icon: Cpu,
    href: "/working-memory",
    gradient: "from-cyan-500 to-blue-500",
  },
  {
    label: "API Keys",
    icon: Key,
    href: "/api-keys",
    gradient: "from-amber-500 to-orange-600",
  },
  {
    label: "Contradictions",
    icon: AlertTriangle,
    href: "/contradictions",
    gradient: "from-red-500 to-rose-600",
  },
  {
    label: "Evaluations",
    icon: BarChart3,
    href: "/evaluations",
    gradient: "from-indigo-500 to-violet-600",
  },
  {
    label: "Webhooks",
    icon: Globe,
    href: "/webhooks",
    gradient: "from-teal-500 to-cyan-600",
  },
  {
    label: "Audit Log",
    icon: ScrollText,
    href: "/audit",
    gradient: "from-slate-400 to-slate-500",
  },
  {
    label: "Settings",
    icon: Settings,
    href: "/settings",
    gradient: "from-gray-400 to-gray-500",
  },
];

interface SidebarProps {
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ isMobileOpen, onMobileClose }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    Cookies.remove("access_token");
    router.push("/login");
  };

  const sidebarContent = (
    <div className="flex flex-col h-full bg-card border-r border-border shadow-sm">
      {/* Logo area */}
      <div className="flex items-center justify-between px-5 py-6">
        <Link href="/dashboard" className="flex items-center gap-3 group">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg shadow-primary/20 group-hover:shadow-primary/40 transition-shadow">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-foreground">AtlasOS</h1>
            <p className="text-[10px] text-muted-foreground leading-none tracking-widest uppercase">
              Console
            </p>
          </div>
        </Link>
        {/* Close button for mobile */}
        {onMobileClose && (
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden text-muted-foreground hover:text-foreground"
            onClick={onMobileClose}
          >
            <X className="h-5 w-5" />
          </Button>
        )}
      </div>

      {/* Separator */}
      <div className="mx-4 h-px bg-border" />

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {routes.map((route) => {
          const isActive = pathname === route.href;
          return (
            <Link
              key={route.href}
              href={route.href}
              onClick={onMobileClose}
              className={cn(
                "group relative flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-primary text-primary-foreground font-semibold shadow-sm shadow-primary/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/80"
              )}
            >
              <route.icon
                className={cn(
                  "h-[18px] w-[18px] shrink-0 transition-colors",
                  isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-foreground"
                )}
              />
              <span className="relative">{route.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="px-3 py-4 space-y-2">
        <div className="mx-1 h-px bg-border mb-2" />

        {/* System status */}
        <div className="px-3 py-2.5 rounded-xl bg-secondary/60 border border-border">
          <div className="flex items-center gap-2 text-xs">
            <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-md shadow-emerald-500/50" />
            <span className="text-muted-foreground">All systems operational</span>
          </div>
        </div>

        {/* Logout */}
        <Button
          onClick={handleLogout}
          variant="ghost"
          className="w-full justify-start text-muted-foreground hover:text-foreground hover:bg-secondary rounded-xl px-3"
          id="logout-btn"
        >
          <LogOut className="h-4 w-4 mr-3" />
          Logout
        </Button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 z-[80]">
        {sidebarContent}
      </div>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {isMobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-[90] bg-black/40 backdrop-blur-sm md:hidden"
              onClick={onMobileClose}
            />

            {/* Drawer */}
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="fixed inset-y-0 left-0 z-[100] w-64 md:hidden"
            >
              {sidebarContent}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

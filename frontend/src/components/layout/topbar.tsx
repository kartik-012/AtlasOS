"use client";

import { Menu, Bell, Search } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TopBarProps {
  onMenuClick: () => void;
}

export function TopBar({ onMenuClick }: TopBarProps) {
  return (
    <header className="sticky top-0 z-50 w-full glass border-b border-black/[0.06]">
      <div className="flex h-14 items-center px-4 md:px-6">
        {/* Mobile menu toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden mr-2 text-muted-foreground hover:text-foreground"
          onClick={onMenuClick}
          id="mobile-menu-toggle"
        >
          <Menu className="h-5 w-5" />
          <span className="sr-only">Toggle sidebar</span>
        </Button>

        {/* Search trigger */}
        <div className="flex-1 flex items-center">
          <Button
            variant="outline"
            className="relative w-full max-w-sm justify-start text-sm text-muted-foreground bg-secondary/60 border-black/[0.06] hover:bg-secondary/80 h-9"
            onClick={() => {
              document.dispatchEvent(new CustomEvent("open-command-menu"));
            }}
          >
            <Search className="mr-2 h-4 w-4" />
            Search memories, tenants...
            <kbd className="pointer-events-none absolute right-2 top-2 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
              <span className="text-xs">⌘</span>K
            </kbd>
          </Button>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-2 ml-4">
          <Button
            variant="ghost"
            size="icon"
            className="relative text-muted-foreground hover:text-foreground"
            id="notifications-btn"
          >
            <Bell className="h-4 w-4" />
            {/* Notification dot */}
            <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-destructive" />
          </Button>

          {/* User avatar */}
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-xs font-bold text-white">
            A
          </div>
        </div>
      </div>
    </header>
  );
}

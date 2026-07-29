"use client";

import { useState } from "react";
import { AuthGuard } from "@/components/layout/auth-guard";
import { Sidebar } from "@/components/layout/sidebar";
import { TopBar } from "@/components/layout/topbar";
import { Toaster } from "sonner";
import { WebSocketProvider } from "@/lib/ws-context";
import { CommandMenu } from "@/components/command-menu";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  return (
    <AuthGuard>
      <WebSocketProvider>
        <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar 
          isMobileOpen={isMobileSidebarOpen} 
          onMobileClose={() => setIsMobileSidebarOpen(false)} 
        />
        
        <div className="flex flex-col flex-1 w-full md:pl-64">
          <TopBar onMenuClick={() => setIsMobileSidebarOpen(true)} />
          
          <main className="flex-1 p-4 md:p-6 lg:p-8 overflow-y-auto">
            {children}
          </main>
        </div>

        <CommandMenu />
        <Toaster theme="light" />
      </div>
      </WebSocketProvider>
    </AuthGuard>
  );
}

"use client";

import { useEffect, useState } from "react";
import { Activity, Database, Users, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import api from "@/lib/api";

export default function DashboardPage() {
  // In a full implementation, these would be fetched from a /api/v1/metrics endpoint
  const [metrics, setMetrics] = useState({
    totalTenants: 0,
    totalMemories: 0,
    activeContradictions: 0,
    apiRequests: 0,
  });

  useEffect(() => {
    // Mock fetch
    setMetrics({
      totalTenants: 12,
      totalMemories: 84392,
      activeContradictions: 24,
      apiRequests: 142093,
    });
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">Overview of your AtlasOS instance.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="glass-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tenants</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-glow">{metrics.totalTenants}</div>
            <p className="text-xs text-muted-foreground">+2 from last month</p>
          </CardContent>
        </Card>
        
        <Card className="glass-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Memories</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-glow">
              {metrics.totalMemories.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">+12,234 from last week</p>
          </CardContent>
        </Card>
        
        <Card className="glass-card border-destructive/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Resolutions</CardTitle>
            <AlertTriangle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive text-glow">
              {metrics.activeContradictions}
            </div>
            <p className="text-xs text-muted-foreground">Requires manual review</p>
          </CardContent>
        </Card>
        
        <Card className="glass-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Requests</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-glow">
              {metrics.apiRequests.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">+18% from last week</p>
          </CardContent>
        </Card>
      </div>

      {/* Future space for charts/graphs */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7 mt-4">
        <Card className="col-span-4 glass-card h-[400px] flex items-center justify-center">
          <p className="text-muted-foreground">Memory Ingestion Chart (Coming Soon)</p>
        </Card>
        <Card className="col-span-3 glass-card h-[400px] flex items-center justify-center">
          <p className="text-muted-foreground">Tenant Usage Breakdown (Coming Soon)</p>
        </Card>
      </div>
    </div>
  );
}

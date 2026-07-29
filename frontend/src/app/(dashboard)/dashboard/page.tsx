"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  Database,
  Users,
  AlertTriangle,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Zap,
  Brain,
  Shield,
} from "lucide-react";
import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/* ─── Mock Data ─── */

const memoryIngestionData = [
  { day: "Mon", memories: 3200, queries: 1800 },
  { day: "Tue", memories: 4100, queries: 2400 },
  { day: "Wed", memories: 3800, queries: 2200 },
  { day: "Thu", memories: 5200, queries: 3100 },
  { day: "Fri", memories: 4800, queries: 2900 },
  { day: "Sat", memories: 3600, queries: 2000 },
  { day: "Sun", memories: 4400, queries: 2600 },
];

const tenantUsageData = [
  { name: "Acme Corp", calls: 28400 },
  { name: "NovaTech", calls: 22100 },
  { name: "Vertex AI", calls: 18900 },
  { name: "SkylineOS", calls: 15200 },
  { name: "DeepLogic", calls: 12800 },
  { name: "QuantumLab", calls: 9400 },
];

const recentActivity = [
  {
    icon: Brain,
    text: "Memory compression completed for Acme Corp",
    time: "2 min ago",
    color: "text-violet-400",
  },
  {
    icon: Users,
    text: 'New tenant "QuantumLab" provisioned',
    time: "15 min ago",
    color: "text-sky-400",
  },
  {
    icon: Shield,
    text: "Contradiction detected in NovaTech memory bank",
    time: "32 min ago",
    color: "text-amber-400",
  },
  {
    icon: Zap,
    text: "Inference latency spike resolved (avg 120ms → 45ms)",
    time: "1 hr ago",
    color: "text-emerald-400",
  },
  {
    icon: Database,
    text: "Qdrant index rebuilt — 84,392 vectors optimized",
    time: "2 hr ago",
    color: "text-teal-400",
  },
];

/* ─── Chart Tooltip ─── */

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name: string; color: string }>;
  label?: string;
}) {
  if (!active || !payload) return null;
  return (
    <div className="glass-card rounded-lg px-3 py-2 shadow-xl border border-border">
      <p className="text-xs font-medium text-foreground mb-1">{label}</p>
      {payload.map((entry, i) => (
        <p key={i} className="text-xs" style={{ color: entry.color }}>
          {entry.name}: {entry.value.toLocaleString()}
        </p>
      ))}
    </div>
  );
}

/* ─── Metric Card ─── */

interface MetricCardProps {
  title: string;
  value: string;
  change: string;
  changeType: "up" | "down";
  icon: React.ElementType;
  gradient: string;
  index: number;
}

function MetricCard({
  title,
  value,
  change,
  changeType,
  icon: Icon,
  gradient,
  index,
}: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1, ease: "easeOut" }}
    >
      <Card className="glass-card-hover group">
        <CardContent className="p-5">
          <div className="flex items-start justify-between mb-4">
            <div
              className={`h-10 w-10 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg opacity-90 group-hover:opacity-100 transition-opacity`}
            >
              <Icon className="h-5 w-5 text-white" />
            </div>
            <div
              className={`flex items-center gap-1 text-xs font-medium ${
                changeType === "up" ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {changeType === "up" ? (
                <ArrowUpRight className="h-3.5 w-3.5" />
              ) : (
                <ArrowDownRight className="h-3.5 w-3.5" />
              )}
              {change}
            </div>
          </div>
          <p className="text-2xl font-bold tracking-tight">{value}</p>
          <p className="text-xs text-muted-foreground mt-1">{title}</p>
        </CardContent>
      </Card>
    </motion.div>
  );
}

/* ─── Dashboard Page ─── */

export default function DashboardPage() {
  const [metrics, setMetrics] = useState({
    totalTenants: 0,
    totalMemories: 0,
    activeContradictions: 0,
    apiRequests: 0,
  });

  useEffect(() => {
    // Simulated API fetch
    setMetrics({
      totalTenants: 12,
      totalMemories: 84392,
      activeContradictions: 24,
      apiRequests: 142093,
    });
  }, []);

  const metricCards: MetricCardProps[] = [
    {
      title: "Total Tenants",
      value: metrics.totalTenants.toLocaleString(),
      change: "+2 this month",
      changeType: "up",
      icon: Users,
      gradient: "from-sky-500 to-blue-600",
      index: 0,
    },
    {
      title: "Total Memories",
      value: metrics.totalMemories.toLocaleString(),
      change: "+12,234 this week",
      changeType: "up",
      icon: Database,
      gradient: "from-violet-500 to-purple-600",
      index: 1,
    },
    {
      title: "Pending Resolutions",
      value: metrics.activeContradictions.toLocaleString(),
      change: "3 critical",
      changeType: "down",
      icon: AlertTriangle,
      gradient: "from-amber-500 to-orange-600",
      index: 2,
    },
    {
      title: "API Requests (7d)",
      value: metrics.apiRequests.toLocaleString(),
      change: "+18% vs last week",
      changeType: "up",
      icon: Activity,
      gradient: "from-emerald-500 to-teal-600",
      index: 3,
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Real-time overview of your AtlasOS instance.
        </p>
      </motion.div>

      {/* Metric cards */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {metricCards.map((card) => (
          <MetricCard key={card.title} {...card} />
        ))}
      </div>

      {/* Charts row */}
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-7">
        {/* Memory Ingestion Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="lg:col-span-4"
        >
          <Card className="glass-card">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  Memory Ingestion
                </CardTitle>
                <span className="text-xs text-muted-foreground">Last 7 days</span>
              </div>
            </CardHeader>
            <CardContent className="pt-2">
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={memoryIngestionData}>
                    <defs>
                      <linearGradient
                        id="gradientMemories"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="0%"
                          stopColor="hsl(246, 80%, 65%)"
                          stopOpacity={0.3}
                        />
                        <stop
                          offset="100%"
                          stopColor="hsl(246, 80%, 65%)"
                          stopOpacity={0}
                        />
                      </linearGradient>
                      <linearGradient
                        id="gradientQueries"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="0%"
                          stopColor="hsl(180, 65%, 50%)"
                          stopOpacity={0.3}
                        />
                        <stop
                          offset="100%"
                          stopColor="hsl(180, 65%, 50%)"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="hsl(var(--border))"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="day"
                      tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 12, fill: "hsl(220, 10%, 55%)" }}
                      axisLine={false}
                      tickLine={false}
                      width={40}
                    />
                    <Tooltip content={<ChartTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="memories"
                      name="Memories Ingested"
                      stroke="hsl(246, 80%, 65%)"
                      strokeWidth={2}
                      fill="url(#gradientMemories)"
                    />
                    <Area
                      type="monotone"
                      dataKey="queries"
                      name="Recall Queries"
                      stroke="hsl(180, 65%, 50%)"
                      strokeWidth={2}
                      fill="url(#gradientQueries)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Tenant Usage Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="lg:col-span-3"
        >
          <Card className="glass-card">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Users className="h-4 w-4 text-accent" />
                  Top Tenants by API Calls
                </CardTitle>
                <span className="text-xs text-muted-foreground">This week</span>
              </div>
            </CardHeader>
            <CardContent className="pt-2">
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={tenantUsageData}
                    layout="vertical"
                    margin={{ left: 10 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="hsl(var(--border))"
                      horizontal={false}
                    />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fontSize: 11, fill: "hsl(220, 10%, 55%)" }}
                      axisLine={false}
                      tickLine={false}
                      width={75}
                    />
                    <Tooltip content={<ChartTooltip />} />
                    <Bar
                      dataKey="calls"
                      name="API Calls"
                      fill="hsl(246, 80%, 65%)"
                      radius={[0, 6, 6, 0]}
                      barSize={18}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Activity Feed */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.5 }}
      >
        <Card className="glass-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {recentActivity.map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: 0.6 + i * 0.08 }}
                  className="flex items-center gap-3 py-2.5 px-2 rounded-lg hover:bg-secondary/50 transition-colors"
                >
                  <div
                    className={`h-8 w-8 rounded-lg bg-secondary/60 flex items-center justify-center shrink-0 ${item.color}`}
                  >
                    <item.icon className="h-4 w-4" />
                  </div>
                  <p className="text-sm text-muted-foreground flex-1 min-w-0 truncate">
                    {item.text}
                  </p>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {item.time}
                  </span>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

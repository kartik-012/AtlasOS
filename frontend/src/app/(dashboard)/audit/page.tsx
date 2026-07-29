"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { ShieldAlert, Search, Filter, Database, Server, User, ChevronDown, ChevronUp } from "lucide-react";
import api from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

const mockAuditLogs = [
  { id: "1", action: "user.login", resource: "auth", actor: "admin@atlasos.dev", timestamp: "2026-07-29T14:50:00Z", ip: "192.168.1.1", details: { method: "password", success: true } },
  { id: "2", action: "api_key.create", resource: "api_keys", actor: "admin@atlasos.dev", timestamp: "2026-07-29T14:30:00Z", ip: "192.168.1.1", details: { name: "Prod Key", permissions: ["read", "write"] } },
  { id: "3", action: "webhook.trigger", resource: "webhooks", actor: "system", timestamp: "2026-07-29T14:15:00Z", ip: "10.0.0.5", details: { endpoint: "https://api.example.com/hook", event: "memory.updated" } },
  { id: "4", action: "memory.contradiction_resolved", resource: "working_memory", actor: "admin@atlasos.dev", timestamp: "2026-07-28T10:00:00Z", ip: "192.168.1.1", details: { contradiction_id: "ctx_123", resolution: "keep_new" } },
  { id: "5", action: "evaluation.run", resource: "evaluations", actor: "system", timestamp: "2026-07-27T02:00:00Z", ip: "10.0.0.5", details: { dataset: "prod_sample_100", metrics: ["latency", "accuracy"] } },
  { id: "6", action: "user.failed_login", resource: "auth", actor: "unknown", timestamp: "2026-07-26T22:10:00Z", ip: "203.0.113.42", details: { reason: "invalid_credentials", attempt: 3 } },
];

export default function AuditPage() {
  const [logs, setLogs] = useState(mockAuditLogs);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const res = await api.get("/audit-logs");
      setLogs(res.data);
    } catch (error) {
      console.warn("Using mock data");
    } finally {
      setLoading(false);
    }
  };

  const filteredLogs = logs.filter(log => {
    const matchesSearch = log.resource.toLowerCase().includes(searchTerm.toLowerCase()) || log.actor.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = actionFilter === "all" || log.action.startsWith(actionFilter);
    return matchesSearch && matchesFilter;
  });

  const getIcon = (action: string) => {
    if (action.startsWith("user")) return <User className="h-4 w-4 text-sky-400" />;
    if (action.startsWith("api_key") || action.startsWith("webhook")) return <Server className="h-4 w-4 text-purple-400" />;
    if (action.startsWith("memory")) return <Database className="h-4 w-4 text-emerald-400" />;
    return <ShieldAlert className="h-4 w-4 text-amber-400" />;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ staggerChildren: 0.1 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-glow">Audit Logs</h1>
          <p className="text-muted-foreground mt-2">Security and operational event timeline.</p>
        </div>
      </div>

      <Card className="glass-card">
        <CardHeader>
          <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
            <div className="relative w-full sm:w-96">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                id="search-audit"
                placeholder="Search resource or actor..."
                className="pl-9 bg-background/50"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Select value={actionFilter} onValueChange={setActionFilter}>
                <SelectTrigger id="filter-audit" className="w-[180px] bg-background/50">
                  <SelectValue placeholder="Action type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Actions</SelectItem>
                  <SelectItem value="user">User & Auth</SelectItem>
                  <SelectItem value="api_key">API Keys</SelectItem>
                  <SelectItem value="webhook">Webhooks</SelectItem>
                  <SelectItem value="memory">Working Memory</SelectItem>
                  <SelectItem value="evaluation">Evaluations</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="relative border-l border-border/50 ml-4 py-4 space-y-8">
            {filteredLogs.map((log, index) => (
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                key={log.id}
                className="relative pl-8"
              >
                <div className="absolute -left-[17px] top-1 h-8 w-8 rounded-full bg-background border border-border flex items-center justify-center">
                  {getIcon(log.action)}
                </div>
                
                <div 
                  className="bg-card/50 border border-border/50 rounded-lg p-4 hover:bg-card/80 transition-colors cursor-pointer"
                  onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
                  id={`audit-row-${log.id}`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold font-mono text-sm">{log.action}</span>
                        <Badge variant="outline" className="text-xs bg-background/50">{log.resource}</Badge>
                      </div>
                      <div className="text-sm text-muted-foreground flex items-center gap-2">
                        <span>{log.actor}</span>
                        <span>•</span>
                        <span>{log.ip}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString()}
                      {expandedId === log.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                  </div>

                  {expandedId === log.id && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="mt-4 pt-4 border-t border-border/50"
                    >
                      <pre className="p-4 rounded-md bg-background/80 font-mono text-xs overflow-x-auto text-muted-foreground border border-border/30">
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    </motion.div>
                  )}
                </div>
              </motion.div>
            ))}
            {filteredLogs.length === 0 && (
              <div className="pl-8 text-muted-foreground">No logs found matching your criteria.</div>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

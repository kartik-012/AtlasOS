"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Brain, Search, Trash2, RefreshCw, Layers, Clock } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

const mockSessions = [
  {
    session_id: "sess_xyz123",
    external_user_id: "user_456",
    ttl: 3600,
    created_at: "2026-07-29T14:00:00Z",
    state: {
      preferences: { theme: "dark", language: "en" },
      recent_topics: ["quantum computing", "AI ethics"],
      context_window: {
        active_entities: ["Alice", "Bob"],
        current_intent: "information_retrieval"
      }
    }
  },
  {
    session_id: "sess_abc987",
    external_user_id: "anon_992",
    ttl: 1200,
    created_at: "2026-07-29T14:30:00Z",
    state: {
      cart: { items: 3, total: 45.99 },
      flow_state: "checkout_step_2"
    }
  }
];

export default function WorkingMemoryPage() {
  const [sessions, setSessions] = useState(mockSessions);
  const [search, setSearch] = useState("");

  const fetchSessions = async () => {
    try {
      const res = await api.get("/working-memory");
      setSessions(res.data);
    } catch {
      console.warn("Using mock data");
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchSessions();
  }, []);

  const handleClear = async (sessionId: string) => {
    try {
      await api.delete(`/working-memory/${sessionId}`);
      setSessions(sessions.filter(s => s.session_id !== sessionId));
      toast.success("Session cleared");
    } catch {
      setSessions(sessions.filter(s => s.session_id !== sessionId));
      toast.success("Mock session cleared");
    }
  };

  const filteredSessions = sessions.filter(s => 
    s.session_id.includes(search) || s.external_user_id.includes(search)
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ staggerChildren: 0.1 }}
      className="space-y-6"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-glow flex items-center">
            <Brain className="mr-3 h-8 w-8 text-primary" />
            Working Memory
          </h1>
          <p className="text-muted-foreground mt-2">Active session state and short-term context cache.</p>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              id="search-memory"
              placeholder="Search ID or User..."
              className="pl-9 bg-background/50"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Button variant="outline" size="icon" onClick={fetchSessions}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {filteredSessions.map((session, index) => (
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            key={session.session_id}
          >
            <Card className="glass-card overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-primary to-accent"></div>
              <CardHeader className="pb-4">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                  <div className="space-y-1">
                    <CardTitle className="flex items-center gap-2">
                      <span className="font-mono text-lg">{session.session_id}</span>
                    </CardTitle>
                    <CardDescription className="flex items-center gap-2">
                      <UserIcon className="w-4 h-4" /> User: <span className="text-foreground">{session.external_user_id}</span>
                      <span className="mx-2">•</span>
                      <Clock className="w-4 h-4" /> Created: {new Date(session.created_at).toLocaleTimeString()}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-4 w-full sm:w-auto">
                    <div className="w-32 space-y-1">
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>TTL</span>
                        <span>{Math.floor(session.ttl / 60)}m</span>
                      </div>
                      <Progress value={(session.ttl / 3600) * 100} className="h-1.5" />
                    </div>
                    <Button 
                      id={`btn-clear-${session.session_id}`}
                      variant="ghost" 
                      size="icon" 
                      className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                      onClick={() => handleClear(session.session_id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="bg-background/80 rounded-md border border-border/50 p-4 font-mono text-sm overflow-x-auto">
                  <pre className="text-muted-foreground">
                    <SyntaxHighlighter data={session.state} />
                  </pre>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
        
        {filteredSessions.length === 0 && (
          <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border/50 rounded-lg">
            <Layers className="h-12 w-12 text-muted-foreground mb-4 opacity-20" />
            <h3 className="text-lg font-medium">No active sessions</h3>
            <p className="text-muted-foreground max-w-sm mt-1">Try adjusting your search criteria or wait for new sessions to begin.</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

import React from "react";
function UserIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

// Simple JSON syntax highlighter component
function SyntaxHighlighter({ data }: { data: unknown }) {
  const jsonStr = JSON.stringify(data, null, 2);
  
  // Very basic regex-based highlighting for demonstration
  const highlighted = jsonStr.split('\n').map((line, i) => {
    if (line.includes(':')) {
      const [key, ...rest] = line.split(':');
      const val = rest.join(':');
      return (
        <div key={i}>
          <span className="text-sky-400">{key}</span>:
          <span className={val.includes('"') ? "text-emerald-400" : "text-amber-400"}>{val}</span>
        </div>
      );
    }
    return <div key={i} className="text-slate-400">{line}</div>;
  });

  return <>{highlighted}</>;
}

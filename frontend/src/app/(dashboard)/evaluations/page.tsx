"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Play, BarChart3, Clock, AlertCircle } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip
} from "recharts";

const mockEvaluations = [
  {
    id: "eval_9", status: "completed", timestamp: "2026-07-29T10:00:00Z", duration: "45s",
    metrics: [
      { name: "Accuracy", value: 0.94, target: 0.90 },
      { name: "Latency", value: 0.85, target: 0.80 },
      { name: "Relevance", value: 0.92, target: 0.85 },
      { name: "Coherence", value: 0.96, target: 0.90 },
      { name: "Safety", value: 1.0, target: 0.99 },
    ]
  },
  {
    id: "eval_8", status: "failed", timestamp: "2026-07-28T15:30:00Z", duration: "12s",
    metrics: [], error: "Dataset connection timeout"
  },
  {
    id: "eval_7", status: "completed", timestamp: "2026-07-25T09:15:00Z", duration: "42s",
    metrics: [
      { name: "Accuracy", value: 0.89, target: 0.90 },
      { name: "Latency", value: 0.82, target: 0.80 },
      { name: "Relevance", value: 0.88, target: 0.85 },
      { name: "Coherence", value: 0.95, target: 0.90 },
      { name: "Safety", value: 1.0, target: 0.99 },
    ]
  },
];

export default function EvaluationsPage() {
  const [evaluations, setEvaluations] = useState(mockEvaluations);
  const [running, setRunning] = useState(false);

  const fetchData = async () => {
    try {
      const res = await api.get("/evaluations");
      setEvaluations(res.data);
    } catch {
      console.warn("Using mock data");
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData();
  }, []);

  const handleRunEvaluation = async () => {
    setRunning(true);
    toast.info("Starting evaluation run...");
    
    setTimeout(() => {
      setRunning(false);
      const newEval = {
        id: `eval_${Math.floor(Math.random() * 1000)}`,
        status: "completed",
        timestamp: new Date().toISOString(),
        duration: "38s",
        metrics: [
          { name: "Accuracy", value: 0.95, target: 0.90 },
          { name: "Latency", value: 0.88, target: 0.80 },
          { name: "Relevance", value: 0.93, target: 0.85 },
          { name: "Coherence", value: 0.97, target: 0.90 },
          { name: "Safety", value: 1.0, target: 0.99 },
        ]
      };
      setEvaluations([newEval, ...evaluations]);
      toast.success("Evaluation completed successfully");
    }, 3000);
  };

  const latestMetrics = evaluations.find(e => e.status === "completed")?.metrics || [];
  const chartData = latestMetrics.map(m => ({
    subject: m.name,
    score: m.value * 100,
    target: m.target * 100,
    fullMark: 100,
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ staggerChildren: 0.1 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-glow">Evaluations</h1>
          <p className="text-muted-foreground mt-2">Monitor model performance and system metrics.</p>
        </div>
        <Button 
          id="btn-run-eval" 
          onClick={handleRunEvaluation} 
          disabled={running}
          className="bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <Play className={`mr-2 h-4 w-4 ${running ? 'animate-pulse' : ''}`} />
          {running ? "Running..." : "Trigger Run"}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card className="glass-card h-full">
            <CardHeader>
              <div className="flex items-center space-x-2">
                <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500/20 to-pink-500/20">
                  <BarChart3 className="h-5 w-5 text-purple-400" />
                </div>
                <CardTitle>Latest Performance</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="h-[300px]">
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="70%" data={chartData}>
                    <PolarGrid stroke="hsl(var(--border))" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                    <Radar name="Score" dataKey="score" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.4} />
                    <Radar name="Target" dataKey="target" stroke="#10b981" fill="transparent" strokeDasharray="3 3" />
                    <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px', color: 'hsl(var(--foreground))' }} />
                  </RadarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  No data available
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-xl font-semibold mb-4">Run History</h3>
          {evaluations.map((run, i) => (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              key={run.id}
            >
              <Card className="glass-card-hover bg-card/40">
                <CardContent className="p-6">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                    <div className="flex items-center gap-4">
                      <Badge variant="outline" className="font-mono bg-background/50">{run.id}</Badge>
                      <div className="text-sm text-muted-foreground flex items-center">
                        <Clock className="w-4 h-4 mr-1" />
                        {new Date(run.timestamp).toLocaleString()} ({run.duration})
                      </div>
                    </div>
                    <Badge className={
                      run.status === 'completed' ? "bg-emerald-500/20 text-emerald-400" :
                      run.status === 'failed' ? "bg-red-500/20 text-red-400" :
                      "bg-amber-500/20 text-amber-400"
                    }>
                      {run.status.toUpperCase()}
                    </Badge>
                  </div>

                  {run.status === 'completed' && run.metrics && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
                      {run.metrics.map(metric => (
                        <div key={metric.name} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">{metric.name}</span>
                            <div className="space-x-2">
                              <span className={metric.value >= metric.target ? "text-emerald-400" : "text-amber-400"}>
                                {(metric.value * 100).toFixed(1)}%
                              </span>
                              <span className="text-muted-foreground/50 text-xs">/ {(metric.target * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                          <div className="h-1.5 w-full bg-background/50 rounded-full overflow-hidden relative">
                            <div 
                              className={`absolute top-0 left-0 h-full ${metric.value >= metric.target ? 'bg-emerald-500' : 'bg-amber-500'}`}
                              style={{ width: `${metric.value * 100}%` }}
                            />
                            <div 
                              className="absolute top-0 h-full w-0.5 bg-white/50 z-10"
                              style={{ left: `${metric.target * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {run.status === 'failed' && (
                    <div className="flex items-center gap-2 text-red-400 bg-red-500/10 p-3 rounded-md border border-red-500/20">
                      <AlertCircle className="w-5 h-5" />
                      <span>{run.error}</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

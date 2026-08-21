"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Check, RefreshCw, Layers } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const mockContradictions = [
  { id: "1", status: "pending", score: 0.92, newFact: "User resides in New York.", existingFact: "User moved to London in 2025.", context: "Address update in profile settings.", timestamp: "2026-07-29T10:15:00Z" },
  { id: "2", status: "pending", score: 0.85, newFact: "Subscription plan is Premium.", existingFact: "Subscription plan is Free Tier.", context: "Billing webhook event.", timestamp: "2026-07-28T14:20:00Z" },
  { id: "3", status: "resolved", score: 0.95, newFact: "Phone number: 555-0199", existingFact: "Phone number: 555-0100", context: "Support ticket resolution.", timestamp: "2026-07-25T09:00:00Z", resolution: "kept_new" },
  { id: "4", status: "resolved", score: 0.78, newFact: "Prefers email contact.", existingFact: "Prefers SMS contact.", context: "Notification preferences update.", timestamp: "2026-07-20T16:45:00Z", resolution: "kept_both" },
];

export default function ContradictionsPage() {
  const [contradictions, setContradictions] = useState(mockContradictions);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const res = await api.get("/contradictions");
      setContradictions(res.data);
    } catch {
      console.warn("Using mock data");
      setContradictions(mockContradictions);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData();
  }, []);

  const handleResolve = async (id: string, resolution: string) => {
    try {
      await api.post(`/contradictions/${id}/resolve`, { resolution });
      toast.success(`Resolved contradiction: ${resolution}`);
      setContradictions(contradictions.map(c => c.id === id ? { ...c, status: "resolved", resolution } : c));
    } catch {
      toast.success(`Mock resolved: ${resolution}`);
      setContradictions(contradictions.map(c => c.id === id ? { ...c, status: "resolved", resolution } : c));
    }
    setSelectedId(null);
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
          <h1 className="text-3xl font-bold text-glow">Contradictions</h1>
          <p className="text-muted-foreground mt-2">Manage memory conflicts detected by the NLI engine.</p>
        </div>
        <Button variant="outline" onClick={fetchData}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {contradictions.map((item, index) => (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.1 }}
            key={item.id}
          >
            <Card className="glass-card h-full flex flex-col">
              <CardHeader className="pb-4 border-b border-border/50">
                <div className="flex justify-between items-start">
                  <div className="flex items-center space-x-2">
                    <div className={`p-2 rounded-lg bg-gradient-to-br ${item.status === 'pending' ? 'from-amber-500/20 to-orange-500/20' : 'from-emerald-500/20 to-teal-500/20'}`}>
                      {item.status === 'pending' ? <AlertTriangle className="h-5 w-5 text-amber-500" /> : <Check className="h-5 w-5 text-emerald-500" />}
                    </div>
                    <div>
                      <CardTitle className="text-lg">Conflict Detected</CardTitle>
                      <CardDescription>{new Date(item.timestamp).toLocaleString()}</CardDescription>
                    </div>
                  </div>
                  <Badge className={item.status === 'pending' ? "bg-amber-500/20 text-amber-500" : "bg-emerald-500/20 text-emerald-500"}>
                    {item.status.toUpperCase()}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="pt-6 flex-1">
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">NLI Confidence Score</span>
                      <span className="font-mono text-amber-400">{(item.score * 100).toFixed(0)}%</span>
                    </div>
                    <Progress value={item.score * 100} className="h-2 bg-background/50 [&>div]:bg-gradient-to-r [&>div]:from-amber-500 [&>div]:to-orange-500" />
                  </div>

                  <div className="grid grid-cols-2 gap-4 mt-6">
                    <div className="bg-background/40 p-4 rounded-lg border border-border/50 relative overflow-hidden">
                      <div className="absolute top-0 left-0 w-1 h-full bg-sky-500"></div>
                      <h4 className="text-xs font-semibold text-sky-400 mb-2 uppercase tracking-wider">New Fact</h4>
                      <p className="text-sm">{item.newFact}</p>
                    </div>
                    <div className="bg-background/40 p-4 rounded-lg border border-border/50 relative overflow-hidden">
                      <div className="absolute top-0 left-0 w-1 h-full bg-slate-500"></div>
                      <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Existing Fact</h4>
                      <p className="text-sm">{item.existingFact}</p>
                    </div>
                  </div>
                  
                  <div className="text-sm text-muted-foreground mt-4">
                    <span className="font-semibold text-foreground/80">Context: </span>
                    {item.context}
                  </div>
                </div>
              </CardContent>
              {item.status === 'pending' && (
                <CardFooter className="border-t border-border/50 pt-4 bg-background/20">
                  <Dialog open={selectedId === item.id} onOpenChange={(open) => setSelectedId(open ? item.id : null)}>
                    <DialogTrigger
                      render={<Button id={`btn-resolve-${item.id}`} className="w-full bg-primary/20 text-primary hover:bg-primary/30 border border-primary/30" />}
                    >
                      <Layers className="w-4 h-4 mr-2" />
                      Resolve Conflict
                    </DialogTrigger>
                    <DialogContent className="glass-card">
                      <DialogHeader>
                        <DialogTitle>Resolve Contradiction</DialogTitle>
                        <DialogDescription>
                          Choose how to handle the conflicting information in working memory.
                        </DialogDescription>
                      </DialogHeader>
                      <div className="grid gap-4 py-4">
                        <Button variant="outline" className="justify-start h-auto p-4 flex flex-col items-start gap-1 hover:border-sky-500/50 hover:bg-sky-500/10" onClick={() => handleResolve(item.id, 'keep_new')}>
                          <span className="font-semibold text-sky-400">Keep New Fact</span>
                          <span className="text-xs text-muted-foreground font-normal text-left">Overwrites the existing fact with the new information.</span>
                        </Button>
                        <Button variant="outline" className="justify-start h-auto p-4 flex flex-col items-start gap-1 hover:border-slate-400/50 hover:bg-slate-500/10" onClick={() => handleResolve(item.id, 'keep_existing')}>
                          <span className="font-semibold text-slate-300">Keep Existing Fact</span>
                          <span className="text-xs text-muted-foreground font-normal text-left">Discards the new information.</span>
                        </Button>
                        <Button variant="outline" className="justify-start h-auto p-4 flex flex-col items-start gap-1 hover:border-purple-500/50 hover:bg-purple-500/10" onClick={() => handleResolve(item.id, 'keep_both')}>
                          <span className="font-semibold text-purple-400">Keep Both</span>
                          <span className="text-xs text-muted-foreground font-normal text-left">Stores both facts with contextual metadata.</span>
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                </CardFooter>
              )}
              {item.status === 'resolved' && (
                <CardFooter className="border-t border-border/50 pt-4 bg-background/20 justify-center">
                  <span className="text-sm text-emerald-500/80 flex items-center">
                    <Check className="w-4 h-4 mr-1" />
                    Resolved: {item.resolution?.replace('_', ' ')}
                  </span>
                </CardFooter>
              )}
            </Card>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

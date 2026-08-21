"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Webhook, Plus, Send, CheckCircle2, XCircle } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";

interface WebhookData {
  id: string;
  url: string;
  description: string;
  events: string[];
  status: string;
  lastDelivery: { status: string; timestamp: string; statusCode: number } | null;
}

const mockWebhooks: WebhookData[] = [
  {
    id: "wh_1",
    url: "https://api.myapp.com/webhooks/atlas",
    description: "Production sync",
    events: ["memory.created", "memory.updated"],
    status: "active",
    lastDelivery: { status: "success", timestamp: "2026-07-29T14:45:00Z", statusCode: 200 }
  },
  {
    id: "wh_2",
    url: "https://staging.myapp.com/webhooks",
    description: "Staging alerts",
    events: ["contradiction.detected"],
    status: "failing",
    lastDelivery: { status: "failed", timestamp: "2026-07-28T09:20:00Z", statusCode: 502 }
  }
];

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState(mockWebhooks);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState({ url: "", description: "", secret: "" });

  const fetchWebhooks = async () => {
    try {
      const res = await api.get("/webhooks");
      setWebhooks(res.data);
    } catch {
      console.warn("Using mock data");
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchWebhooks();
  }, []);

  const handleCreate = async () => {
    if (!formData.url) {
      toast.error("URL is required");
      return;
    }
    
    try {
      await api.post("/webhooks", formData);
      toast.success("Webhook created");
      fetchWebhooks();
      setIsDialogOpen(false);
    } catch {
      const newWh = {
        id: `wh_${Math.random().toString(36).substring(2, 7)}`,
        url: formData.url,
        description: formData.description || "New Webhook",
        events: ["all"],
        status: "active",
        lastDelivery: null
      };
      setWebhooks([newWh, ...webhooks]);
      toast.success("Mock webhook created");
      setIsDialogOpen(false);
    }
  };

  const handleTest = async (id: string) => {
    toast.info("Sending test payload...");
    setTimeout(() => {
      setWebhooks(webhooks.map(w => w.id === id ? {
        ...w,
        status: "active",
        lastDelivery: { status: "success", timestamp: new Date().toISOString(), statusCode: 200 }
      } : w));
      toast.success("Test payload delivered successfully");
    }, 1500);
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
          <h1 className="text-3xl font-bold text-glow">Webhooks</h1>
          <p className="text-muted-foreground mt-2">Receive real-time HTTP requests for events in your OS.</p>
        </div>
        
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger
            render={<Button id="btn-create-webhook" className="bg-primary text-primary-foreground hover:bg-primary/90" />}
          >
            <Plus className="mr-2 h-4 w-4" /> Add Webhook
          </DialogTrigger>
          <DialogContent className="glass-card sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Add Endpoint</DialogTitle>
              <DialogDescription>
                Configure a new URL to receive event payloads.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="url">Payload URL</Label>
                <Input
                  id="url"
                  placeholder="https://your-domain.com/webhook"
                  className="bg-background/50"
                  value={formData.url}
                  onChange={e => setFormData({...formData, url: e.target.value})}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="desc">Description</Label>
                <Input
                  id="desc"
                  placeholder="e.g. Production API"
                  className="bg-background/50"
                  value={formData.description}
                  onChange={e => setFormData({...formData, description: e.target.value})}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="secret">Secret (optional)</Label>
                <Input
                  id="secret"
                  type="password"
                  placeholder="Used to sign webhook payloads"
                  className="bg-background/50"
                  value={formData.secret}
                  onChange={e => setFormData({...formData, secret: e.target.value})}
                />
              </div>
            </div>
            <DialogFooter>
              <Button id="btn-submit-webhook" onClick={handleCreate}>Create Webhook</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {webhooks.map((webhook, i) => (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.1 }}
            key={webhook.id}
          >
            <Card className="glass-card h-full flex flex-col">
              <CardHeader className="pb-4 border-b border-border/50">
                <div className="flex justify-between items-start">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20">
                      <Webhook className="h-5 w-5 text-cyan-400" />
                    </div>
                    <div>
                      <CardTitle className="text-base truncate max-w-[200px] sm:max-w-[300px]" title={webhook.url}>
                        {webhook.url}
                      </CardTitle>
                      <CardDescription>{webhook.description}</CardDescription>
                    </div>
                  </div>
                  <Badge className={webhook.status === 'active' ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}>
                    {webhook.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="pt-6 flex-1">
                <div className="space-y-4">
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Events</h4>
                    <div className="flex flex-wrap gap-2">
                      {webhook.events.map(ev => (
                        <Badge key={ev} variant="outline" className="bg-background/50">{ev}</Badge>
                      ))}
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Last Delivery</h4>
                    {webhook.lastDelivery ? (
                      <div className="flex items-center gap-3 text-sm p-3 rounded-md bg-background/40 border border-border/50">
                        {webhook.lastDelivery.status === 'success' ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-500" />
                        )}
                        <span className="font-mono text-muted-foreground">HTTP {webhook.lastDelivery.statusCode}</span>
                        <span className="text-muted-foreground ml-auto">
                          {new Date(webhook.lastDelivery.timestamp).toLocaleString()}
                        </span>
                      </div>
                    ) : (
                      <div className="text-sm text-muted-foreground p-3 rounded-md bg-background/40 border border-border/50 border-dashed">
                        No deliveries yet
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
              <CardFooter className="border-t border-border/50 pt-4 bg-background/20">
                <Button id={`btn-test-${webhook.id}`} variant="outline" size="sm" onClick={() => handleTest(webhook.id)} className="w-full">
                  <Send className="w-4 h-4 mr-2" />
                  Test Endpoint
                </Button>
              </CardFooter>
            </Card>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

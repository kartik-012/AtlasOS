"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Plus, Key, Copy, Check, Trash2 } from "lucide-react";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

const mockApiKeys = [
  { id: "1", name: "Production App", keyPrefix: "ak_prod_xyz", permissions: ["read", "write"], status: "active", createdAt: "2026-07-20T10:00:00Z", lastUsed: "2026-07-29T14:30:00Z" },
  { id: "2", name: "Staging Service", keyPrefix: "ak_stag_abc", permissions: ["read", "write"], status: "active", createdAt: "2026-06-15T09:12:00Z", lastUsed: "2026-07-28T11:20:00Z" },
  { id: "3", name: "Read-only Bot", keyPrefix: "ak_bot_123", permissions: ["read"], status: "revoked", createdAt: "2026-01-10T14:00:00Z", lastUsed: "2026-03-05T08:45:00Z" },
];

export default function ApiKeysPage() {
  const [keys, setKeys] = useState(mockApiKeys);
  const [newKeyName, setNewKeyName] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [createdKey, setCreatedKey] = useState("");
  const [copied, setCopied] = useState(false);

  const fetchKeys = async () => {
    try {
      const res = await api.get("/api-keys");
      setKeys(res.data);
    } catch {
      console.warn("Using mock data for API keys");
      setKeys(mockApiKeys);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchKeys();
  }, []);

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) {
      toast.error("Please enter a key name");
      return;
    }
    try {
      const res = await api.post("/api-keys", { name: newKeyName });
      setCreatedKey(res.data.key); // Unmasked key
      fetchKeys();
      toast.success("API key created");
    } catch {
      // Mock creation
      const newKey = {
        id: Math.random().toString(),
        name: newKeyName,
        keyPrefix: "ak_mock_" + Math.random().toString(36).substring(2, 7),
        permissions: ["read", "write"],
        status: "active",
        createdAt: new Date().toISOString(),
        lastUsed: "Never",
      };
      setKeys([newKey, ...keys]);
      setCreatedKey(`ak_mock_${Math.random().toString(36).substring(2, 20)}`);
      toast.success("Mock API key created");
    }
  };

  const handleRevoke = async (id: string) => {
    try {
      await api.delete(`/api-keys/${id}`);
      fetchKeys();
      toast.success("Key revoked successfully");
    } catch {
      setKeys(keys.map(k => k.id === id ? { ...k, status: "revoked" } : k));
      toast.success("Mock key revoked");
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(createdKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success("Copied to clipboard");
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
          <h1 className="text-3xl font-bold text-glow">API Keys</h1>
          <p className="text-muted-foreground mt-2">Manage programmatic access to your AtlasOS projects.</p>
        </div>
        
        <Dialog open={isDialogOpen} onOpenChange={(open) => {
          setIsDialogOpen(open);
          if (!open) setCreatedKey("");
        }}>
          <DialogTrigger
            render={<Button id="btn-create-key" className="bg-primary text-primary-foreground hover:bg-primary/90" />}
          >
            <Plus className="mr-2 h-4 w-4" /> Create Secret Key
          </DialogTrigger>
          <DialogContent className="glass-card sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Create new secret key</DialogTitle>
              <DialogDescription>
                This key will have access to all environments in this project.
              </DialogDescription>
            </DialogHeader>
            {!createdKey ? (
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="new-key-name"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    placeholder="e.g. Production Backend"
                    className="bg-background/50"
                  />
                </div>
              </div>
            ) : (
              <div className="grid gap-4 py-4">
                <div className="rounded-md bg-amber-500/10 p-4 border border-amber-500/20">
                  <p className="text-sm text-amber-500 mb-2 font-medium">Please save this secret key somewhere safe and accessible.</p>
                  <p className="text-sm text-muted-foreground">For security reasons, you won&apos;t be able to view it again through your AtlasOS account. If you lose this secret key, you&apos;ll need to generate a new one.</p>
                </div>
                <div className="flex items-center space-x-2">
                  <Input id="created-key-value" value={createdKey} readOnly className="font-mono bg-background/50" />
                  <Button size="icon" variant="outline" onClick={copyToClipboard}>
                    {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
            )}
            <DialogFooter>
              {!createdKey ? (
                <Button id="btn-submit-key" onClick={handleCreateKey}>Create Key</Button>
              ) : (
                <Button onClick={() => setIsDialogOpen(false)}>Done</Button>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="glass-card">
        <CardHeader>
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-lg bg-gradient-to-br from-indigo-500/20 to-purple-500/20">
              <Key className="h-5 w-5 text-indigo-400" />
            </div>
            <div>
              <CardTitle>Secret Keys</CardTitle>
              <CardDescription>Active keys that can access your API</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Key Prefix</TableHead>
                <TableHead>Permissions</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Last Used</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                    No API keys found.
                  </TableCell>
                </TableRow>
              ) : (
                keys.map((key, index) => (
                  <motion.tr
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    key={key.id}
                    className="group"
                  >
                    <TableCell className="font-medium">{key.name}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{key.keyPrefix}...</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {key.permissions.map(p => (
                          <Badge key={p} variant="outline" className="text-xs bg-background/50">
                            {p}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={key.status === "active" ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20" : "bg-red-500/20 text-red-400 hover:bg-red-500/20"}>
                        {key.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(key.createdAt).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {key.lastUsed !== "Never" ? new Date(key.lastUsed).toLocaleDateString() : "Never"}
                    </TableCell>
                    <TableCell className="text-right">
                      {key.status === "active" && (
                        <Button
                          id={`btn-revoke-${key.id}`}
                          variant="ghost"
                          size="sm"
                          className="text-red-400 hover:text-red-300 hover:bg-red-500/10 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={() => handleRevoke(key.id)}
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
                          Revoke
                        </Button>
                      )}
                    </TableCell>
                  </motion.tr>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </motion.div>
  );
}

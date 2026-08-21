"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import api from "@/lib/api";

type Tenant = {
  id: string;
  name: string;
  resolution_policy: string;
  created_at: string;
};

export default function TenantsPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // New Tenant Form State
  const [newName, setNewName] = useState("");
  const [newPolicy, setNewPolicy] = useState("most_recent_wins");

  const fetchTenants = async () => {
    try {
      setIsLoading(true);
      const res = await api.get("/tenants");
      setTenants(res.data);
    } catch {
      // Fallback demo data when backend isn't running
      setTenants([
        { id: "123e4567-e89b-12d3-a456-426614174000", name: "Acme Corp", resolution_policy: "confidence_weighted", created_at: new Date().toISOString() },
        { id: "987e6543-e21b-12d3-a456-426614174000", name: "Globex Inc", resolution_policy: "manual_review", created_at: new Date().toISOString() },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchTenants();
  }, []);

  const handleCreateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/tenants", {
        name: newName,
        resolution_policy: newPolicy,
      });
      toast.success("Tenant created successfully");
      setIsDialogOpen(false);
      setNewName("");
      fetchTenants();
    } catch {
      toast.error("Failed to create tenant");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Tenants</h2>
          <p className="text-muted-foreground">Manage organizations and their contradiction policies.</p>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger>
            <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
              <Plus className="mr-2 h-4 w-4" /> Add Tenant
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px] bg-card border-white/10">
            <form onSubmit={handleCreateTenant}>
              <DialogHeader>
                <DialogTitle>Create New Tenant</DialogTitle>
                <DialogDescription>
                  Create a new isolated organization space.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="name">Organization Name</Label>
                  <Input
                    id="name"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    className="bg-background/50 border-white/10"
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="policy">Resolution Policy</Label>
                  <Select
                    value={newPolicy}
                    onValueChange={(val) => {
                      if (val !== null) setNewPolicy(val);
                    }}
                  >
                    <SelectTrigger className="bg-background/50 border-white/10">
                      <SelectValue placeholder="Select a policy" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="most_recent_wins">Most Recent Wins</SelectItem>
                      <SelectItem value="confidence_weighted">Confidence Weighted</SelectItem>
                      <SelectItem value="manual_review">Manual Review</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button type="submit" className="bg-primary text-primary-foreground">Create</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle>Active Organizations</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-white/10 hover:bg-transparent">
                <TableHead>ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Resolution Policy</TableHead>
                <TableHead>Created At</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center h-24">Loading...</TableCell>
                </TableRow>
              ) : tenants.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center h-24 text-muted-foreground">No tenants found.</TableCell>
                </TableRow>
              ) : (
                tenants.map((tenant) => (
                  <TableRow key={tenant.id} className="border-white/5 hover:bg-white/5 transition-colors">
                    <TableCell className="font-mono text-xs text-muted-foreground">{tenant.id}</TableCell>
                    <TableCell className="font-medium">{tenant.name}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors border-transparent bg-primary/20 text-primary">
                        {tenant.resolution_policy.replace(/_/g, " ")}
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {format(new Date(tenant.created_at), "MMM d, yyyy")}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm">Manage API Keys</Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck, Zap } from "lucide-react";
import Cookies from "js-cookie";
import { toast } from "sonner";
import axios from "axios";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@atlasos.dev");
  const [password, setPassword] = useState("admin12345");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // Attempt login to FastAPI Backend
      const res = await axios.post("http://localhost:8000/api/v1/auth/login", {
        email,
        password,
      });

      if (res.data?.access_token) {
        Cookies.set("access_token", res.data.access_token, { expires: 1 });
        toast.success("Authenticated with AtlasOS API Server");
        router.push("/dashboard");
        return;
      }
    } catch {
      // Fallback for standalone demo
      Cookies.set("access_token", "demo-token-123", { expires: 1 });
      toast.success("Welcome to AtlasOS Console");
      router.push("/dashboard");
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickDemo = () => {
    setEmail("admin@atlasos.dev");
    setPassword("admin12345");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background relative overflow-hidden">
      {/* Dynamic Background Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/20 rounded-full blur-[120px] pointer-events-none" />
      
      <div className="relative z-10 w-full max-w-md p-4">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center h-12 w-12 rounded-2xl bg-gradient-to-br from-primary to-accent shadow-lg shadow-primary/30 mb-4">
            <Zap className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-glow mb-2">AtlasOS</h1>
          <p className="text-muted-foreground text-sm">AI Memory Operating System Console</p>
        </div>

        <Card className="glass-card border-primary/20 shadow-2xl">
          <form onSubmit={handleLogin}>
            <CardHeader>
              <CardTitle className="text-2xl">Sign In</CardTitle>
              <CardDescription>Enter administrator credentials to manage memory pipelines.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input 
                  id="email" 
                  type="email" 
                  placeholder="admin@atlasos.dev" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-background/50 border-white/10 focus-visible:ring-primary" 
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input 
                  id="password" 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-background/50 border-white/10 focus-visible:ring-primary" 
                  required
                />
              </div>

              <div className="p-3 bg-secondary/50 rounded-lg border border-border/50 text-xs text-muted-foreground flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <span>Default Seed Admin: <strong className="text-foreground">admin@atlasos.dev</strong></span>
                </div>
                <button
                  type="button"
                  onClick={handleQuickDemo}
                  className="text-primary hover:underline font-semibold"
                >
                  Fill
                </button>
              </div>
            </CardContent>
            <CardFooter>
              <Button type="submit" className="w-full bg-primary hover:bg-primary/90 text-primary-foreground transition-all duration-300" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Connecting to AtlasOS...
                  </>
                ) : (
                  "Access System Console"
                )}
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}

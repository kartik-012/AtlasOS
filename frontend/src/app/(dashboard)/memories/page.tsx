"use client";

import { useState } from "react";
import { Search } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function MemoryExplorerPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<any[]>([]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSearching(true);
    
    // Mocking search for UI demonstration. In production, this would hit /api/v1/memories/search
    setTimeout(() => {
      setResults([
        {
          id: "mem-1",
          type: "semantic",
          content: "The company headquarters is located in San Francisco.",
          importance_score: 0.85,
          similarity_score: 0.92,
        },
        {
          id: "mem-2",
          type: "episodic",
          content: "User visited the pricing page on Tuesday.",
          importance_score: 0.45,
          similarity_score: 0.65,
        }
      ]);
      setIsSearching(false);
    }, 800);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Memory Explorer</h2>
        <p className="text-muted-foreground">Search and inspect the vector space across all tenants.</p>
      </div>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle>Semantic Search</CardTitle>
          <CardDescription>Execute a natural language query against the Qdrant vector database.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input 
                placeholder="What is the capital of..." 
                className="pl-9 bg-background/50 border-white/10 h-10"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Button type="submit" className="h-10 px-8" disabled={isSearching || !searchQuery}>
              {isSearching ? "Searching..." : "Search"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {results.length > 0 && (
        <div className="space-y-4 mt-8">
          <h3 className="text-xl font-semibold">Results</h3>
          <div className="grid gap-4">
            {results.map((result) => (
              <Card key={result.id} className="glass-card border-white/5 hover:border-primary/30 transition-colors">
                <CardContent className="p-4 flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${result.type === 'semantic' ? 'bg-primary/20 text-primary' : 'bg-emerald-500/20 text-emerald-500'}`}>
                        {result.type}
                      </span>
                      <span className="text-xs text-muted-foreground font-mono">{result.id}</span>
                    </div>
                    <p className="text-sm">{result.content}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-muted-foreground mb-1">Composite Score</div>
                    <div className="text-xl font-bold text-glow">
                      {((result.similarity_score * 0.75) + (result.importance_score * 0.25)).toFixed(2)}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

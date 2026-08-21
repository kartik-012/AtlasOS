"use client";

import { useState } from "react";
import { Search, Network, Brain, Activity } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

type MemoryResult = {
  id: string;
  type: string;
  content: string;
  importance_score: number;
  similarity_score: number;
  composite_score: number;
};

type GraphNode = {
  id: string;
  name: string;
  type: string;
};

type GraphEdge = {
  id: string;
  source: string;
  target: string;
  relation: string;
};

export default function MemoryExplorerPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<MemoryResult[]>([]);
  const [activeTab, setActiveTab] = useState<"search" | "graph">("search");
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] }>({
    nodes: [
      { id: "1", name: "User", type: "PERSON" },
      { id: "2", name: "Dark Mode", type: "PREFERENCE" },
      { id: "3", name: "Google", type: "ORGANIZATION" },
    ],
    edges: [
      { id: "e1", source: "User", target: "Dark Mode", relation: "PREFERS" },
      { id: "e2", source: "User", target: "Google", relation: "WORKS_FOR" },
    ],
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSearching(true);

    setTimeout(() => {
      setResults([
        {
          id: "mem-101",
          type: "semantic",
          content: "User prefers dark mode and uses TypeScript with FastAPI.",
          importance_score: 0.92,
          similarity_score: 0.95,
          composite_score: 0.94,
        },
        {
          id: "mem-102",
          type: "episodic",
          content: "User stated they are preparing for a Google Senior Engineer interview.",
          importance_score: 0.88,
          similarity_score: 0.85,
          composite_score: 0.87,
        },
      ]);
      setGraphData({
        nodes: [
          { id: "1", name: "User", type: "PERSON" },
          { id: "2", name: "Dark Mode", type: "PREFERENCE" },
          { id: "3", name: "Google Interview", type: "EVENT" },
          { id: "4", name: "FastAPI", type: "TECH" },
        ],
        edges: [
          { id: "e1", source: "User", target: "Dark Mode", relation: "PREFERS" },
          { id: "e2", source: "User", target: "Google Interview", relation: "PREPARES_FOR" },
          { id: "e3", source: "User", target: "FastAPI", relation: "USES" },
        ],
      });
      setIsSearching(false);
    }, 600);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Memory & Graph Mesh Explorer</h2>
          <p className="text-muted-foreground">
            Hierarchical memory search, Ebbinghaus decay analysis, and entity graph visualization.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={activeTab === "search" ? "default" : "outline"}
            onClick={() => setActiveTab("search")}
            className="flex items-center gap-2"
          >
            <Brain className="h-4 w-4" /> Vector Search
          </Button>
          <Button
            variant={activeTab === "graph" ? "default" : "outline"}
            onClick={() => setActiveTab("graph")}
            className="flex items-center gap-2"
          >
            <Network className="h-4 w-4" /> Knowledge Graph Mesh
          </Button>
        </div>
      </div>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle>Hybrid Dense-Sparse RRF Search</CardTitle>
          <CardDescription>
            Search memories with real-time Ebbinghaus retrievability decay and entity expansion.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search user preferences, facts, or technical stack..."
                className="pl-9 bg-background/50 border-white/10 h-10"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Button type="submit" className="h-10 px-8" disabled={isSearching || !searchQuery}>
              {isSearching ? "Querying Engine..." : "Search Engine"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {activeTab === "search" ? (
        results.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-xl font-semibold flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" /> Top Ranked Memories (Reciprocal Rank Fusion)
            </h3>
            <div className="grid gap-4">
              {results.map((result) => (
                <Card
                  key={result.id}
                  className="glass-card border-white/5 hover:border-primary/30 transition-colors"
                >
                  <CardContent className="p-4 flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <span
                          className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                            result.type === "semantic"
                              ? "bg-primary/20 text-primary"
                              : "bg-emerald-500/20 text-emerald-500"
                          }`}
                        >
                          {result.type}
                        </span>
                        <span className="text-xs text-muted-foreground font-mono">{result.id}</span>
                      </div>
                      <p className="text-sm font-medium">{result.content}</p>
                      <div className="flex gap-4 mt-3 text-xs text-muted-foreground">
                        <span>Similarity: {result.similarity_score.toFixed(2)}</span>
                        <span>Importance: {result.importance_score.toFixed(2)}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-muted-foreground mb-1">Composite Score</div>
                      <div className="text-xl font-bold text-glow">{result.composite_score.toFixed(2)}</div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )
      ) : (
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Network className="h-5 w-5 text-emerald-400" /> Knowledge Graph Mesh Visualizer
            </CardTitle>
            <CardDescription>
              Entity triples (Subject-Predicate-Object) connected across memories.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-black/40 border border-white/10 rounded-lg p-6 min-h-[300px] flex flex-col justify-center items-center">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full">
                {graphData.nodes.map((node) => (
                  <div
                    key={node.id}
                    className="p-4 rounded-lg bg-white/5 border border-white/10 flex flex-col justify-between"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-primary">{node.name}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-white/10 font-mono">
                        {node.type}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Edges:
                      {graphData.edges
                        .filter((e) => e.source === node.name || e.target === node.name)
                        .map((e) => (
                          <div key={e.id} className="mt-1 font-mono text-emerald-400">
                            {e.source} --[{e.relation}]--&gt; {e.target}
                          </div>
                        ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

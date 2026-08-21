"use client";

import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

interface WebSocketContextType {
  isConnected: boolean;
}

const WebSocketContext = createContext<WebSocketContextType>({ isConnected: false });

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);
  const maxReconnectAttempts = 3; // Stop after 3 failed attempts when backend is offline

  const connect = () => {
    if (typeof window === "undefined") return;
    if (reconnectAttemptRef.current >= maxReconnectAttempts) {
      console.log("[WebSocket] Backend unavailable, stopping reconnect attempts.");
      return;
    }

    try {
      const ws = new WebSocket("ws://localhost:8000/api/v1/ws");
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptRef.current = 0;
        console.log("[WebSocket] Connected");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "EVALUATION_COMPLETED") {
            toast.success("Evaluation Completed", { description: data.message || "An evaluation task has finished." });
          } else if (data.type === "ERROR") {
            toast.error("System Error", { description: data.message || "An error occurred." });
          } else if (data.type === "SUCCESS") {
            toast.success("Success", { description: data.message || "Operation completed." });
          } else {
            toast(data.message || `Event: ${data.type}`);
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        reconnectAttemptRef.current += 1;
        if (reconnectAttemptRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptRef.current), 10000);
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        // Silently handle - onclose will fire next
      };
    } catch {
      // WebSocket constructor failed, backend not available
    }
  };

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <WebSocketContext.Provider value={{ isConnected }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  return useContext(WebSocketContext);
}

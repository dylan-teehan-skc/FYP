"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { EventOut } from "@/lib/types";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:9000";

interface UseWebSocketOptions {
  workflowId?: string;
  enabled?: boolean;
}

interface UseWebSocketReturn {
  events: EventOut[];
  connected: boolean;
  error: string | null;
}

export function useWebSocket({
  workflowId,
  enabled = true,
}: UseWebSocketOptions = {}): UseWebSocketReturn {
  const [events, setEvents] = useState<EventOut[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!enabled) return;

    const params = workflowId ? `?workflow_id=${workflowId}` : "";
    const ws = new WebSocket(`${WS_BASE}/ws/events${params}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setError(null);
    };

    ws.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data) as EventOut;
        setEvents((prev) => [...prev, event]);
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection error");
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      if (enabled) {
        reconnectRef.current = setTimeout(connect, 3000);
      }
    };
  }, [workflowId, enabled]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { events, connected, error };
}

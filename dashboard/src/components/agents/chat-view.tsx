"use client";

import { useEffect, useRef } from "react";
import { ChatMessage } from "./chat-message";
import type { EventOut } from "@/lib/types";

interface ChatViewProps {
  events: EventOut[];
  isLive: boolean;
}

export function ChatView({ events, isLive }: ChatViewProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isLive && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [events.length, isLive]);

  return (
    <div className="space-y-3">
      {events.map((event) => (
        <ChatMessage key={event.event_id} event={event} allEvents={events} />
      ))}
      {isLive && (
        <div className="flex items-center gap-2 px-2 py-3 text-sm text-muted-foreground">
          <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          Listening for events...
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}

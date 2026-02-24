"use client";

import { Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function InfoTooltip({ text }: { text: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Info className="inline h-3.5 w-3.5 cursor-help text-muted-foreground/60 hover:text-muted-foreground" />
      </TooltipTrigger>
      <TooltipContent
        side="bottom"
        className="max-w-xs px-3 py-2 text-xs leading-relaxed"
      >
        {text}
      </TooltipContent>
    </Tooltip>
  );
}

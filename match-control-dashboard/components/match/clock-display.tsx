"use client"

import { useMatch } from "@/lib/match-context"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const periodLabels: Record<string, string> = {
  "1H": "1st Half",
  HT: "Half Time",
  "2H": "2nd Half",
  ET1: "Extra Time 1",
  ET2: "Extra Time 2",
  PEN: "Penalties",
}

const statusColors: Record<string, string> = {
  running: "bg-green-500",
  paused: "bg-yellow-500",
  stopped: "bg-red-500",
}

export function ClockDisplay() {
  const { match } = useMatch()
  const { clock } = match

  return (
    <div className="flex flex-col items-center gap-3">
      {/* Main clock display */}
      <div className="font-mono text-6xl md:text-8xl font-bold tracking-wider text-foreground tabular-nums">
        {clock.formatted}
      </div>

      {/* Period and status badges */}
      <div className="flex items-center gap-3">
        <Badge variant="secondary" className="text-sm px-3 py-1">
          {periodLabels[clock.period] || clock.period}
        </Badge>

        <div className="flex items-center gap-2">
          <div className={cn("w-3 h-3 rounded-full animate-pulse", statusColors[clock.status])} />
          <span className="text-sm font-medium uppercase text-muted-foreground">{clock.status}</span>
        </div>

        {clock.added_minutes > 0 && (
          <Badge variant="outline" className="text-sm">
            +{clock.added_minutes} min added
          </Badge>
        )}
      </div>
    </div>
  )
}

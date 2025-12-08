"use client"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { Team, Player } from "@/lib/types"
import { cn } from "@/lib/utils"

interface TeamCardProps {
  team: Team
  players: Player[]
  score: number
  side: "home" | "away"
}

export function TeamCard({ team, players, score, side }: TeamCardProps) {
  return (
    <Card className={cn("flex-1", side === "home" ? "border-l-4 border-l-blue-500" : "border-r-4 border-r-red-500")}>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-4">
          <img
            src={team.logo_url || `/placeholder.svg?height=64&width=64&query=${encodeURIComponent(team.name)} logo`}
            alt={team.name}
            className="w-16 h-16 object-contain"
          />
          <div className="flex-1">
            <h3 className="text-xl font-bold">{team.name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline">{team.formation}</Badge>
              <div
                className="w-4 h-4 rounded-full border border-border"
                style={{ backgroundColor: team.kit_color }}
                title="Kit color"
              />
            </div>
          </div>
          <div className="text-5xl font-bold tabular-nums">{score}</div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-sm text-muted-foreground mb-2">Starting XI</div>
        <ScrollArea className="h-[200px]">
          <div className="space-y-1">
            {players.map((player) => (
              <div key={player.id} className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-muted/50">
                <span className="font-mono text-sm w-8 text-muted-foreground">#{player.jersey_number}</span>
                <span className="flex-1">{player.name}</span>
                <Badge variant="secondary" className="text-xs">
                  {player.position}
                </Badge>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

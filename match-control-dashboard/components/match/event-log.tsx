"use client"

import type React from "react"

import { useMatch } from "@/lib/match-context"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Trash2, Goal, AlertTriangle, Users, Target } from "lucide-react"
import { cn } from "@/lib/utils"
import type { EventType } from "@/lib/types"

const eventIcons: Record<EventType, React.ReactNode> = {
  goal: <Goal className="h-4 w-4 text-green-500" />,
  own_goal: <Goal className="h-4 w-4 text-red-500" />,
  yellow_card: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
  red_card: <AlertTriangle className="h-4 w-4 text-red-500" />,
  second_yellow: <AlertTriangle className="h-4 w-4 text-orange-500" />,
  substitution: <Users className="h-4 w-4 text-blue-500" />,
  penalty_scored: <Target className="h-4 w-4 text-green-500" />,
  penalty_missed: <Target className="h-4 w-4 text-red-500" />,
}

const eventLabels: Record<EventType, string> = {
  goal: "GOAL",
  own_goal: "OWN GOAL",
  yellow_card: "YELLOW CARD",
  red_card: "RED CARD",
  second_yellow: "2ND YELLOW",
  substitution: "SUBSTITUTION",
  penalty_scored: "PENALTY SCORED",
  penalty_missed: "PENALTY MISSED",
}

export function EventLog() {
  const { match, removeEvent } = useMatch()
  const events = [...match.events].reverse()

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Event Log</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px]">
          {events.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">No events recorded yet</div>
          ) : (
            <div className="space-y-2">
              {events.map((event) => (
                <div
                  key={event.id}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-lg border",
                    event.team === "home" ? "bg-blue-500/5 border-blue-500/20" : "bg-red-500/5 border-red-500/20",
                  )}
                >
                  <div className="flex items-center gap-2 min-w-[60px]">
                    <span className="font-mono text-sm text-muted-foreground">{event.display_minute}'</span>
                    {eventIcons[event.event_type]}
                  </div>

                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Badge variant={event.team === "home" ? "default" : "destructive"} className="text-xs">
                        {event.team === "home" ? match.home_team.name : match.away_team.name}
                      </Badge>
                      <span className="font-medium text-sm">{eventLabels[event.event_type]}</span>
                    </div>
                    <p className="text-sm mt-1">
                      {event.player_name}
                      {event.secondary_player_name && (
                        <span className="text-muted-foreground">
                          {event.event_type === "substitution"
                            ? ` → ${event.secondary_player_name}`
                            : ` (Assist: ${event.secondary_player_name})`}
                        </span>
                      )}
                    </p>
                  </div>

                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={() => removeEvent(event.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

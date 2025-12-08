"use client"

import type React from "react"

import { useMatch } from "@/lib/match-context"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Trash2, Goal, AlertTriangle, Users, Target, ScrollText } from "lucide-react"
import { cn } from "@/lib/utils"
import type { EventType } from "@/lib/types"

const eventIcons: Record<EventType, React.ReactNode> = {
  goal: <Goal className="h-5 w-5 text-green-500" />,
  own_goal: <Goal className="h-5 w-5 text-red-500" />,
  yellow_card: <AlertTriangle className="h-5 w-5 text-yellow-500" />,
  red_card: <AlertTriangle className="h-5 w-5 text-red-500" />,
  second_yellow: <AlertTriangle className="h-5 w-5 text-orange-500" />,
  substitution: <Users className="h-5 w-5 text-blue-500" />,
  penalty_scored: <Target className="h-5 w-5 text-green-500" />,
  penalty_missed: <Target className="h-5 w-5 text-red-500" />,
}

const eventLabels: Record<EventType, string> = {
  goal: "Goal",
  own_goal: "Own Goal",
  yellow_card: "Yellow Card",
  red_card: "Red Card",
  second_yellow: "Second Yellow",
  substitution: "Substitution",
  penalty_scored: "Penalty Scored",
  penalty_missed: "Penalty Missed",
}

export default function EventsPage() {
  const { match, removeEvent } = useMatch()
  const events = [...match.events].sort((a, b) => a.display_minute - b.display_minute)

  // Group events by period
  const eventsByPeriod = events.reduce(
    (acc, event) => {
      if (!acc[event.period]) {
        acc[event.period] = []
      }
      acc[event.period].push(event)
      return acc
    },
    {} as Record<string, typeof events>,
  )

  const periodOrder = ["1H", "2H", "ET1", "ET2", "PEN"]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Event Log</h1>
        <Badge variant="secondary">{match.events.length} events</Badge>
      </div>

      {/* Match info header */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center gap-8">
            <div className="text-center">
              <div className="font-bold">{match.home_team.name}</div>
              <div className="text-3xl font-bold text-blue-500">{match.home_score}</div>
            </div>
            <div className="text-2xl text-muted-foreground">vs</div>
            <div className="text-center">
              <div className="font-bold">{match.away_team.name}</div>
              <div className="text-3xl font-bold text-red-500">{match.away_score}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {events.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <div className="rounded-full bg-muted p-4 mb-4">
              <ScrollText className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="font-medium text-lg mb-1">No Events Yet</h3>
            <p className="text-muted-foreground text-sm">
              Events will appear here as they are recorded during the match.
            </p>
          </CardContent>
        </Card>
      ) : (
        <ScrollArea className="h-[calc(100vh-300px)]">
          <div className="space-y-6">
            {periodOrder.map((period) => {
              const periodEvents = eventsByPeriod[period]
              if (!periodEvents || periodEvents.length === 0) return null

              return (
                <Card key={period}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Badge variant="outline">{period}</Badge>
                      <span className="text-muted-foreground font-normal">
                        {periodEvents.length} event{periodEvents.length !== 1 ? "s" : ""}
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {periodEvents.map((event) => (
                        <div
                          key={event.id}
                          className={cn(
                            "flex items-start gap-4 p-4 rounded-lg border",
                            event.team === "home"
                              ? "bg-blue-500/5 border-blue-500/20"
                              : "bg-red-500/5 border-red-500/20",
                          )}
                        >
                          <div className="flex items-center gap-3 min-w-[80px]">
                            <span className="font-mono text-lg font-bold">{event.display_minute}'</span>
                            {eventIcons[event.event_type]}
                          </div>

                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant={event.team === "home" ? "default" : "destructive"}>
                                {event.team === "home" ? match.home_team.name : match.away_team.name}
                              </Badge>
                              <span className="font-medium">{eventLabels[event.event_type]}</span>
                            </div>
                            <p className="text-lg">
                              {event.player_name}
                              {event.secondary_player_name && (
                                <span className="text-muted-foreground">
                                  {event.event_type === "substitution"
                                    ? ` → ${event.secondary_player_name}`
                                    : ` (Assist: ${event.secondary_player_name})`}
                                </span>
                              )}
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {new Date(event.created_at).toLocaleTimeString()}
                            </p>
                          </div>

                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-muted-foreground hover:text-destructive"
                            onClick={() => removeEvent(event.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </ScrollArea>
      )}
    </div>
  )
}

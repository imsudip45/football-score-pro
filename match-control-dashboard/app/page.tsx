"use client"

import type React from "react"

import { useMatch } from "@/lib/match-context"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import Link from "next/link"
import { Gamepad2, Clock, Goal, AlertTriangle } from "lucide-react"
import type { EventType } from "@/lib/types"

const eventIcons: Record<EventType, React.ReactNode> = {
  goal: <Goal className="h-4 w-4 text-green-500" />,
  own_goal: <Goal className="h-4 w-4 text-red-500" />,
  yellow_card: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
  red_card: <AlertTriangle className="h-4 w-4 text-red-500" />,
  second_yellow: <AlertTriangle className="h-4 w-4 text-orange-500" />,
  substitution: <Gamepad2 className="h-4 w-4 text-blue-500" />,
  penalty_scored: <Goal className="h-4 w-4 text-green-500" />,
  penalty_missed: <Goal className="h-4 w-4 text-red-500" />,
}

export default function DashboardPage() {
  const { match, hasActiveMatch } = useMatch()

  if (!hasActiveMatch) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <div className="rounded-full bg-muted p-6 mb-6">
          <Gamepad2 className="h-12 w-12 text-muted-foreground" />
        </div>
        <h2 className="text-2xl font-bold mb-2">No Match in Progress</h2>
        <p className="text-muted-foreground mb-6 max-w-md">
          There is no active match at the moment. Load a fixture or go to Match Control to start.
        </p>
        <div className="flex gap-4">
          <Button asChild variant="outline">
            <Link href="/fixtures">View Fixtures</Link>
          </Button>
          <Button asChild>
            <Link href="/match-control">Go to Match Control</Link>
          </Button>
        </div>
      </div>
    )
  }

  const recentEvents = [...match.events].reverse().slice(0, 5)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Badge
          variant={match.status === "live" ? "default" : "secondary"}
          className={match.status === "live" ? "bg-green-500" : ""}
        >
          {match.status.toUpperCase()}
        </Badge>
      </div>

      {/* Match summary card */}
      <Card className="overflow-hidden">
        <CardHeader className="bg-gradient-to-r from-blue-500/10 to-red-500/10">
          <CardTitle className="text-lg">Current Match</CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            {/* Home team */}
            <div className="flex items-center gap-4 flex-1">
              <img
                src={
                  match.home_team.logo_url ||
                  `/placeholder.svg?height=64&width=64&query=${encodeURIComponent(match.home_team.name)} logo`
                }
                alt={match.home_team.name}
                className="w-16 h-16 object-contain"
              />
              <div>
                <div className="font-bold text-lg">{match.home_team.name}</div>
                <div className="text-sm text-muted-foreground">Home</div>
              </div>
            </div>

            {/* Score and time */}
            <div className="text-center px-8">
              <div className="text-5xl font-bold tabular-nums">
                {match.home_score} - {match.away_score}
              </div>
              <div className="flex items-center justify-center gap-2 mt-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="font-mono text-lg">{match.clock.formatted}</span>
                <Badge variant="outline" className="text-xs">
                  {match.clock.period}
                </Badge>
              </div>
            </div>

            {/* Away team */}
            <div className="flex items-center gap-4 flex-1 justify-end text-right">
              <div>
                <div className="font-bold text-lg">{match.away_team.name}</div>
                <div className="text-sm text-muted-foreground">Away</div>
              </div>
              <img
                src={
                  match.away_team.logo_url ||
                  `/placeholder.svg?height=64&width=64&query=${encodeURIComponent(match.away_team.name)} logo`
                }
                alt={match.away_team.name}
                className="w-16 h-16 object-contain"
              />
            </div>
          </div>

          <div className="mt-6 pt-6 border-t">
            <Button asChild className="w-full">
              <Link href="/match-control">
                <Gamepad2 className="mr-2 h-4 w-4" />
                Go to Match Control
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recent events */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recent Events</CardTitle>
        </CardHeader>
        <CardContent>
          {recentEvents.length === 0 ? (
            <div className="text-center text-muted-foreground py-4">No events recorded yet</div>
          ) : (
            <ScrollArea className="h-[200px]">
              <div className="space-y-2">
                {recentEvents.map((event) => (
                  <div key={event.id} className="flex items-center gap-3 p-2 rounded hover:bg-muted/50">
                    <span className="font-mono text-sm text-muted-foreground w-8">{event.display_minute}'</span>
                    {eventIcons[event.event_type]}
                    <Badge variant={event.team === "home" ? "default" : "destructive"} className="text-xs">
                      {event.team === "home" ? match.home_team.name : match.away_team.name}
                    </Badge>
                    <span className="text-sm">{event.player_name}</span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

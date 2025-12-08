"use client"

import { ClockDisplay } from "@/components/match/clock-display"
import { ClockControls } from "@/components/match/clock-controls"
import { TeamCard } from "@/components/match/team-card"
import { StatsPanel } from "@/components/match/stats-panel"
import { PossessionBar } from "@/components/match/possession-bar"
import { QuickEvents } from "@/components/match/quick-events"
import { EventLog } from "@/components/match/event-log"
import { PenaltyShootoutPanel } from "@/components/match/penalty-shootout-panel"
import { MatchActions } from "@/components/match/match-actions"
import { WeatherWidget } from "@/components/match/weather-widget"
import { useMatch } from "@/lib/match-context"
import { Badge } from "@/components/ui/badge"

export default function MatchControlPage() {
  const { match } = useMatch()


  if (!match?.match_id) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-muted-foreground">
        <p>Waiting for match data from backend…</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with match status */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Match Control</h1>
        <Badge
          variant={match.status === "live" ? "default" : "secondary"}
          className={match.status === "live" ? "bg-green-500" : ""}
        >
          {match.status.toUpperCase()}
        </Badge>
      </div>

      {/* Clock and Weather section */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 bg-card rounded-xl p-6 border text-center">
          <ClockDisplay />
          <div className="mt-6">
            <ClockControls />
          </div>
        </div>
        <div className="lg:col-span-1">
          <WeatherWidget />
        </div>
      </div>

      {/* Team cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TeamCard team={match.home_team} players={match.home_lineup} score={match.home_score} side="home" />
        <TeamCard team={match.away_team} players={match.away_lineup} score={match.away_score} side="away" />
      </div>

      {/* Stats and possession */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StatsPanel />
        <PossessionBar />
      </div>

      {/* Penalty shootout panel (only shown during penalties) */}
      <PenaltyShootoutPanel />

      {/* Quick events */}
      <QuickEvents />

      {/* Event log */}
      <EventLog />

      {/* Match actions */}
      <MatchActions />
    </div>
  )
}

"use client"

import { useMatch } from "@/lib/match-context"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Minus, Plus } from "lucide-react"

const statLabels: Record<string, string> = {
  shots: "Shots",
  shots_on_target: "Shots on Target",
  corners: "Corners",
  fouls: "Fouls",
  yellow_cards: "Yellow Cards",
  red_cards: "Red Cards",
}

const editableStats = ["shots", "shots_on_target", "corners", "fouls"] as const

export function StatsPanel() {
  const { match, updateStat } = useMatch()
  const { stats } = match

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Match Statistics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {Object.entries(statLabels).map(([key, label]) => {
            const homeValue = stats.home[key as keyof typeof stats.home]
            const awayValue = stats.away[key as keyof typeof stats.away]
            const isEditable = editableStats.includes(key as (typeof editableStats)[number])

            return (
              <div key={key} className="flex items-center gap-4">
                {/* Home team controls */}
                <div className="flex items-center gap-2 flex-1 justify-end">
                  {isEditable && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => updateStat("home", key as keyof typeof stats.home, -1)}
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                  )}
                  <span className="font-bold text-lg w-8 text-center tabular-nums">{homeValue}</span>
                  {isEditable && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => updateStat("home", key as keyof typeof stats.home, 1)}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  )}
                </div>

                {/* Stat label */}
                <div className="w-32 text-center text-sm text-muted-foreground">{label}</div>

                {/* Away team controls */}
                <div className="flex items-center gap-2 flex-1">
                  {isEditable && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => updateStat("away", key as keyof typeof stats.away, -1)}
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                  )}
                  <span className="font-bold text-lg w-8 text-center tabular-nums">{awayValue}</span>
                  {isEditable && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => updateStat("away", key as keyof typeof stats.away, 1)}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

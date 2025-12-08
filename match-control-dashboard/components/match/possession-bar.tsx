"use client"

import { useMatch } from "@/lib/match-context"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function PossessionBar() {
  const { match, updatePossession } = useMatch()
  const { possession } = match

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Possession</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Possession bar */}
        <div className="flex items-center gap-4">
          <span className="font-bold text-lg w-12 text-blue-500 tabular-nums">{possession.home_pct}%</span>
          <div className="flex-1 h-6 rounded-full overflow-hidden flex">
            <div className="bg-blue-500 transition-all duration-300" style={{ width: `${possession.home_pct}%` }} />
            <div className="bg-red-500 transition-all duration-300" style={{ width: `${possession.away_pct}%` }} />
          </div>
          <span className="font-bold text-lg w-12 text-right text-red-500 tabular-nums">{possession.away_pct}%</span>
        </div>

        {/* Possession toggle buttons */}
        <div className="flex items-center justify-center gap-3">
          <Button
            variant={possession.current === "home" ? "default" : "outline"}
            onClick={() => updatePossession("home")}
            className={cn(possession.current === "home" && "bg-blue-500 hover:bg-blue-600")}
          >
            Home
          </Button>
          <Button variant={possession.current === null ? "default" : "outline"} onClick={() => updatePossession(null)}>
            Neutral
          </Button>
          <Button
            variant={possession.current === "away" ? "default" : "outline"}
            onClick={() => updatePossession("away")}
            className={cn(possession.current === "away" && "bg-red-500 hover:bg-red-600")}
          >
            Away
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

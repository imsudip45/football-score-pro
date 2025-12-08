"use client"

import { useState } from "react"
import { useMatch } from "@/lib/match-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Play, Pause, Square, SkipForward } from "lucide-react"

export function ClockControls() {
  const { match, startClock, pauseClock, stopClock, nextPeriod, setAddedTime } = useMatch()
  const { clock } = match
  const [addedTimeInput, setAddedTimeInput] = useState("")

  const handleSetAddedTime = () => {
    const minutes = Number.parseInt(addedTimeInput, 10)
    if (!isNaN(minutes) && minutes >= 0) {
      setAddedTime(minutes)
      setAddedTimeInput("")
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Main clock controls */}
      <div className="flex items-center justify-center gap-3">
        {clock.status === "stopped" || clock.status === "paused" ? (
          <Button size="lg" onClick={startClock} className="bg-green-600 hover:bg-green-700 text-white min-w-[120px]">
            <Play className="mr-2 h-5 w-5" />
            {clock.status === "paused" ? "Resume" : "Start"}
          </Button>
        ) : (
          <Button size="lg" onClick={pauseClock} className="bg-yellow-600 hover:bg-yellow-700 text-white min-w-[120px]">
            <Pause className="mr-2 h-5 w-5" />
            Pause
          </Button>
        )}

        <Button
          size="lg"
          variant="destructive"
          onClick={stopClock}
          disabled={clock.status === "stopped"}
          className="min-w-[120px]"
        >
          <Square className="mr-2 h-5 w-5" />
          Stop
        </Button>

        <Button
          size="lg"
          variant="outline"
          onClick={nextPeriod}
          disabled={clock.period === "PEN"}
          className="min-w-[140px] bg-transparent"
        >
          <SkipForward className="mr-2 h-5 w-5" />
          Next Period
        </Button>
      </div>

      {/* Added time control */}
      <div className="flex items-end gap-3 justify-center">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="added-time" className="text-sm text-muted-foreground">
            Stoppage Time (min)
          </Label>
          <Input
            id="added-time"
            type="number"
            min="0"
            max="15"
            placeholder="0"
            value={addedTimeInput}
            onChange={(e) => setAddedTimeInput(e.target.value)}
            className="w-24"
          />
        </div>
        <Button onClick={handleSetAddedTime} variant="secondary">
          Set Added Time
        </Button>
      </div>
    </div>
  )
}

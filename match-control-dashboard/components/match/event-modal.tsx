"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useMatch } from "@/lib/match-context"
import type { EventType, Player } from "@/lib/types"

interface EventModalProps {
  open: boolean
  onClose: () => void
  eventType: EventType
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

const needsSecondaryPlayer: EventType[] = ["goal", "substitution"]

export function EventModal({ open, onClose, eventType }: EventModalProps) {
  const { match, addEvent } = useMatch()
  const [team, setTeam] = useState<"home" | "away">("home")
  const [playerId, setPlayerId] = useState("")
  const [secondaryPlayerId, setSecondaryPlayerId] = useState("")

  const players: Player[] = team === "home" ? match.home_lineup : match.away_lineup
  const requiresSecondary = needsSecondaryPlayer.includes(eventType)

  const selectedPlayer = players.find((p) => p.id === playerId)
  const secondaryPlayer = players.find((p) => p.id === secondaryPlayerId)

  const handleSubmit = () => {
    if (!selectedPlayer) return

    addEvent({
      event_type: eventType,
      team,
      player_name: selectedPlayer.name,
      secondary_player_name: secondaryPlayer?.name,
    })

    // Reset and close
    setPlayerId("")
    setSecondaryPlayerId("")
    onClose()
  }

  const handleClose = () => {
    setPlayerId("")
    setSecondaryPlayerId("")
    setTeam("home")
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Record {eventLabels[eventType]}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Team selector */}
          <div className="space-y-2">
            <Label>Team</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={team === "home" ? "default" : "outline"}
                onClick={() => {
                  setTeam("home")
                  setPlayerId("")
                  setSecondaryPlayerId("")
                }}
                className="flex-1"
              >
                {match.home_team.name}
              </Button>
              <Button
                type="button"
                variant={team === "away" ? "default" : "outline"}
                onClick={() => {
                  setTeam("away")
                  setPlayerId("")
                  setSecondaryPlayerId("")
                }}
                className="flex-1"
              >
                {match.away_team.name}
              </Button>
            </div>
          </div>

          {/* Player selector */}
          <div className="space-y-2">
            <Label>{eventType === "substitution" ? "Player Out" : "Player"}</Label>
            <Select value={playerId} onValueChange={setPlayerId}>
              <SelectTrigger>
                <SelectValue placeholder="Select player" />
              </SelectTrigger>
              <SelectContent>
                {players.map((player) => (
                  <SelectItem key={player.id} value={player.id}>
                    #{player.jersey_number} {player.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Secondary player selector */}
          {requiresSecondary && (
            <div className="space-y-2">
              <Label>{eventType === "substitution" ? "Player In" : "Assist (optional)"}</Label>
              <Select value={secondaryPlayerId} onValueChange={setSecondaryPlayerId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select player" />
                </SelectTrigger>
                <SelectContent>
                  {eventType !== "substitution" && <SelectItem value="none">None</SelectItem>}
                  {players
                    .filter((p) => p.id !== playerId)
                    .map((player) => (
                      <SelectItem key={player.id} value={player.id}>
                        #{player.jersey_number} {player.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!playerId || (eventType === "substitution" && !secondaryPlayerId)}>
            Confirm
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

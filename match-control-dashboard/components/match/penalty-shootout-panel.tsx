"use client"

import { useState } from "react"
import { useMatch } from "@/lib/match-context"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { Check, X, Plus, Trash2, Trophy } from "lucide-react"
import { cn } from "@/lib/utils"

export function PenaltyShootoutPanel() {
  const { match, addPenaltyKick, removePenaltyKick } = useMatch()
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedTeam, setSelectedTeam] = useState<"home" | "away">("home")
  const [playerId, setPlayerId] = useState("")
  const [scored, setScored] = useState(true)

  if (match.clock.period !== "PEN") return null

  const shootout = match.penalty_shootout
  if (!shootout) return null

  const players = selectedTeam === "home" ? match.home_lineup : match.away_lineup
  const selectedPlayer = players.find((p) => p.id === playerId)

  const handleAddKick = () => {
    if (!selectedPlayer) return
    addPenaltyKick(selectedTeam, selectedPlayer.name, scored)
    setPlayerId("")
    setScored(true)
    setModalOpen(false)
  }

  const openModal = (team: "home" | "away") => {
    setSelectedTeam(team)
    setModalOpen(true)
  }

  return (
    <>
      <Card className="border-2 border-yellow-500/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Trophy className="h-5 w-5 text-yellow-500" />
              Penalty Shootout
            </CardTitle>
            {shootout.winner && (
              <Badge className="bg-yellow-500 text-black">
                {shootout.winner === "home" ? match.home_team.name : match.away_team.name} Wins!
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {/* Score display */}
          <div className="flex items-center justify-center gap-8 mb-6">
            <div className="text-center">
              <div className="text-sm text-muted-foreground mb-1">{match.home_team.name}</div>
              <div className="text-4xl font-bold text-blue-500">{shootout.home_scored}</div>
            </div>
            <div className="text-2xl text-muted-foreground">-</div>
            <div className="text-center">
              <div className="text-sm text-muted-foreground mb-1">{match.away_team.name}</div>
              <div className="text-4xl font-bold text-red-500">{shootout.away_scored}</div>
            </div>
          </div>

          {/* Kicks lists */}
          <div className="grid grid-cols-2 gap-4">
            {/* Home kicks */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-blue-500">Home Kicks</span>
                <Button size="sm" variant="outline" onClick={() => openModal("home")}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add
                </Button>
              </div>
              <div className="space-y-2">
                {shootout.home_kicks.map((kick) => (
                  <div
                    key={kick.id}
                    className={cn(
                      "flex items-center gap-2 p-2 rounded border",
                      kick.scored ? "bg-green-500/10 border-green-500/30" : "bg-red-500/10 border-red-500/30",
                    )}
                  >
                    <span className="font-mono text-sm w-6">{kick.order}.</span>
                    {kick.scored ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <X className="h-4 w-4 text-red-500" />
                    )}
                    <span className="flex-1 text-sm">{kick.player_name}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => removePenaltyKick("home", kick.id)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            {/* Away kicks */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-red-500">Away Kicks</span>
                <Button size="sm" variant="outline" onClick={() => openModal("away")}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add
                </Button>
              </div>
              <div className="space-y-2">
                {shootout.away_kicks.map((kick) => (
                  <div
                    key={kick.id}
                    className={cn(
                      "flex items-center gap-2 p-2 rounded border",
                      kick.scored ? "bg-green-500/10 border-green-500/30" : "bg-red-500/10 border-red-500/30",
                    )}
                  >
                    <span className="font-mono text-sm w-6">{kick.order}.</span>
                    {kick.scored ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <X className="h-4 w-4 text-red-500" />
                    )}
                    <span className="flex-1 text-sm">{kick.player_name}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => removePenaltyKick("away", kick.id)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Add kick modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Penalty Kick</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Player</Label>
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

            <div className="flex items-center space-x-2">
              <Checkbox id="scored" checked={scored} onCheckedChange={(checked) => setScored(checked as boolean)} />
              <Label htmlFor="scored" className="cursor-pointer">
                Penalty Scored
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddKick} disabled={!playerId}>
              Add Kick
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

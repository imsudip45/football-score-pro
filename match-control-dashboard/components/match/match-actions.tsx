"use client"

import { useState } from "react"
import { useMatch } from "@/lib/match-context"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { AlertTriangle, Cloud, Flag, Loader2, Trash2 } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { fixturesApi } from "@/lib/api"

export function MatchActions() {
  const { match, endMatch, deleteMatch } = useMatch()
  const { toast } = useToast()
  const [endModalOpen, setEndModalOpen] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [ending, setEnding] = useState(false)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const handleEndMatch = async () => {
    const summary = {
      homeName: match.home_team.name,
      awayName: match.away_team.name,
      homeScore: match.home_score,
      awayScore: match.away_score,
    }

    setEnding(true)
    const success = await endMatch()
    setEnding(false)
    setEndModalOpen(false)

    if (success) {
      toast({
        title: "Match Ended",
        description: `Final Score: ${summary.homeName} ${summary.homeScore} - ${summary.awayScore} ${summary.awayName}`,
      })
    } else {
      toast({
        title: "Unable to end match",
        description: "The backend did not accept the finish request. Check the server logs and try again.",
        variant: "destructive",
      })
    }
  }

  const handleSync = async () => {
    if (!match.fixture_id) {
      toast({
        title: "Nothing to sync",
        description: "This match wasn't loaded from a fixture, so there is no fixture to send the result to.",
        variant: "destructive",
      })
      return
    }
    setSyncing(true)
    const result = await fixturesApi.uploadResult(match.fixture_id)
    setSyncing(false)
    if (result.data?.success) {
      toast({
        title: "Synced to Cloud",
        description: "The final result was sent to the fixtures server.",
      })
    } else {
      toast({
        title: "Sync failed",
        description: result.error || "The fixtures server did not accept the result.",
        variant: "destructive",
      })
    }
  }

  const handleDeleteMatch = async () => {
    const summary = {
      homeName: match.home_team.name,
      awayName: match.away_team.name,
    }

    setDeleting(true)
    const success = await deleteMatch()
    setDeleting(false)
    setDeleteModalOpen(false)

    if (success) {
      toast({
        title: "Match Deleted",
        description: `${summary.homeName} vs ${summary.awayName} has been removed from the local backend.`,
      })
    } else {
      toast({
        title: "Unable to delete match",
        description: "The backend returned an error while deleting the match.",
        variant: "destructive",
      })
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-center gap-4 pt-4 border-t">
        <Button
          variant="destructive"
          size="lg"
          onClick={() => setEndModalOpen(true)}
          disabled={match.status === "finished" || ending}
        >
          {ending ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <Flag className="mr-2 h-5 w-5" />}
          {ending ? "Ending…" : "End Match"}
        </Button>

        <Button variant="outline" size="lg" onClick={handleSync} disabled={syncing || match.status !== "finished"}>
          <Cloud className="mr-2 h-5 w-5" />
          {syncing ? "Syncing..." : "Sync to Cloud"}
        </Button>

        {match.match_id && match.status === "created" && (
          <Button
            variant="outline"
            size="lg"
            onClick={() => setDeleteModalOpen(true)}
            className="border-destructive/50 text-destructive hover:bg-destructive/10"
            disabled={deleting}
          >
            {deleting ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <Trash2 className="mr-2 h-5 w-5" />}
            {deleting ? "Deleting…" : "Delete Match"}
          </Button>
        )}
      </div>

      <Dialog open={endModalOpen} onOpenChange={setEndModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              End Match?
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to end this match? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 rounded-lg border bg-muted p-4">
            <div className="text-center">
              <div className="text-lg font-bold">
                {match.home_team.name} {match.home_score} - {match.away_score} {match.away_team.name}
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                {match.clock.period} • {match.clock.formatted}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEndModalOpen(false)} disabled={ending}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleEndMatch} disabled={ending}>
              {ending ? "Ending…" : "End Match"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Match?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove the match and all associated data from the local backend.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteMatch}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleting}
            >
              {deleting ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

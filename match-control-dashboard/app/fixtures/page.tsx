"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Calendar, MapPin, Trophy, Check, RefreshCw, Cloud, Loader2, Upload, Play, Clock, Trash2 } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { useMatch } from "@/lib/match-context"
import { BASE_URL, fixturesApi, matchApi, type BackendMatch, type CloudFixture, type CloudTournament } from "@/lib/api"

type LocalMatchSummary = {
  match: BackendMatch
  homeName: string
  awayName: string
  createdAt?: string | null
}

export default function FixturesPage() {
  const { toast } = useToast()
  const { deleteMatch: deleteMatchFromContext } = useMatch()
  const [tournaments, setTournaments] = useState<CloudTournament[]>([])
  const [selectedTournament, setSelectedTournament] = useState<string>("all")
  const [fixtures, setFixtures] = useState<CloudFixture[]>([])
  const [selectedFixture, setSelectedFixture] = useState<CloudFixture | null>(null)
  const [loadedFixtureId, setLoadedFixtureId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingFixture, setLoadingFixture] = useState(false)
  const [uploadingFixture, setUploadingFixture] = useState<string | null>(null)
  const [localMatches, setLocalMatches] = useState<LocalMatchSummary[]>([])
  const [loadingLocal, setLoadingLocal] = useState(true)
  const [deletingMatchId, setDeletingMatchId] = useState<string | null>(null)

  // Status badge helper
  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "live":
        return (
          <Badge className="bg-red-500 animate-pulse">
            <Play className="h-3 w-3 mr-1" />
            LIVE
          </Badge>
        )
      case "finished":
        return (
          <Badge className="bg-gray-500">
            <Check className="h-3 w-3 mr-1" />
            Finished
          </Badge>
        )
      case "scheduled":
      default:
        return (
          <Badge variant="outline" className="text-blue-500 border-blue-500">
            <Clock className="h-3 w-3 mr-1" />
            Scheduled
          </Badge>
        )
    }
  }

  const handleUploadToCloud = async (fixture: CloudFixture) => {
    setUploadingFixture(fixture.id)
    try {
      const response = await fetch(`${BASE_URL}/fixtures/upload/${fixture.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      
      if (response.ok) {
        const result = await response.json()
        toast({
          title: "Uploaded to Cloud",
          description: `Match result for ${fixture.home_team.name} vs ${fixture.away_team.name} has been uploaded.`,
        })
      } else {
        const error = await response.json()
        toast({
          title: "Upload Failed",
          description: error.detail || "Failed to upload match data to cloud",
          variant: "destructive",
        })
      }
    } catch (error) {
      toast({
        title: "Upload Failed",
        description: "Could not connect to backend. Is it running?",
        variant: "destructive",
      })
    } finally {
      setUploadingFixture(null)
    }
  }

  const fetchLocalMatches = useCallback(async () => {
    setLoadingLocal(true)
    try {
      const result = await matchApi.listMatches("created")

      if (result.data) {
        const enriched = await Promise.all(
          result.data.map(async (match) => {
            const state = await matchApi.getMatchState(match.id)
            const homeMeta = (state.data?.home_team as Record<string, unknown> | undefined) ?? undefined
            const awayMeta = (state.data?.away_team as Record<string, unknown> | undefined) ?? undefined

            const homeName =
              (homeMeta?.name as string | undefined) ||
              (homeMeta?.short_name as string | undefined) ||
              match.home_team_id
            const awayName =
              (awayMeta?.name as string | undefined) ||
              (awayMeta?.short_name as string | undefined) ||
              match.away_team_id

            return {
              match,
              homeName,
              awayName,
              createdAt: match.created_at || null,
            }
          })
        )

        setLocalMatches(enriched)
      } else {
        setLocalMatches([])
        if (result.error) {
          toast({
            title: "Error",
            description: "Failed to load local matches",
            variant: "destructive",
          })
        }
      }
    } catch (error) {
      console.error("Failed to load local matches", error)
      toast({
        title: "Error",
        description: "Failed to load local matches",
        variant: "destructive",
      })
    } finally {
      setLoadingLocal(false)
    }
  }, [toast])

  // Fetch tournaments on mount
  useEffect(() => {
    fetchTournaments()
  }, [])

  // Fetch fixtures when tournament changes
  useEffect(() => {
    fetchFixtures()
  }, [selectedTournament])

  useEffect(() => {
    fetchLocalMatches()
  }, [fetchLocalMatches])

  const fetchTournaments = async () => {
    const result = await fixturesApi.getCloudTournaments()
    if (result.data) {
      setTournaments(result.data)
    } else {
      toast({
        title: "Error",
        description: "Failed to load tournaments. Is the backend running?",
        variant: "destructive",
      })
    }
  }

  const fetchFixtures = async () => {
    setLoading(true)
    try {
      if (selectedTournament === "all") {
        const result = await fixturesApi.getCloudFixtures()
        if (result.data) {
          setFixtures(result.data)
        }
      } else {
        const result = await fixturesApi.getCloudTournamentFixtures(selectedTournament)
        if (result.data?.fixtures) {
          setFixtures(result.data.fixtures)
        }
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load fixtures",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleLoadFixture = async () => {
    if (!selectedFixture) return

    setLoadingFixture(true)
    try {
      const result = await fixturesApi.loadCloudFixture(selectedFixture.id)
      
      if (result.data?.success) {
        setLoadedFixtureId(selectedFixture.id)
        setSelectedFixture(null)
        await fetchLocalMatches()
        toast({
          title: "Fixture Loaded",
          description: `${selectedFixture.home_team.name} vs ${selectedFixture.away_team.name} is ready for match control.`,
        })
      } else {
        toast({
          title: "Error",
          description: result.error || "Failed to load fixture",
          variant: "destructive",
        })
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load fixture from cloud",
        variant: "destructive",
      })
    } finally {
      setLoadingFixture(false)
    }
  }

  const handleDeleteLocalMatch = async (summary: LocalMatchSummary) => {
    setDeletingMatchId(summary.match.id)
    try {
      const success = await deleteMatchFromContext(summary.match.id)

      if (success) {
        if (summary.match.fixture_id && summary.match.fixture_id === loadedFixtureId) {
          setLoadedFixtureId(null)
        }

        toast({
          title: "Match Deleted",
          description: `${summary.homeName} vs ${summary.awayName} has been removed from the local backend.`,
        })

        await fetchLocalMatches()
      } else {
        toast({
          title: "Unable to delete match",
          description: "The backend returned an error while deleting the match.",
          variant: "destructive",
        })
      }
    } finally {
      setDeletingMatchId(null)
    }
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return { date: "TBD", time: "TBD" }
    const date = new Date(dateString)
    return {
      date: date.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" }),
      time: date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }),
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold">Fixtures</h1>
          <Badge variant="outline" className="gap-1">
            <Cloud className="h-3 w-3" />
            Cloud
          </Badge>
        </div>
        <div className="flex items-center gap-4">
          <Select value={selectedTournament} onValueChange={setSelectedTournament}>
            <SelectTrigger className="w-[250px]">
              <SelectValue placeholder="Select tournament" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Tournaments</SelectItem>
              {tournaments.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name} ({t.fixture_count || 0})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={fetchFixtures} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
          <Badge variant="secondary">{fixtures.length} fixtures</Badge>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : fixtures.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No fixtures available</p>
            <p className="text-sm text-muted-foreground mt-2">
              Make sure the cloud backend (port 3001) and local backend (port 8000) are running.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {fixtures.map((fixture) => {
            const { date, time } = formatDate(fixture.scheduled_date)
            const isLoaded = loadedFixtureId === fixture.id

            return (
              <Card key={fixture.id} className={isLoaded ? "border-green-500 bg-green-500/5" : ""}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-6">
                    {/* Date & time */}
                    <div className="text-center min-w-[100px]">
                      <div className="flex items-center gap-1 text-muted-foreground text-sm mb-1">
                        <Calendar className="h-4 w-4" />
                        {date}
                      </div>
                      <div className="font-bold text-lg">{time}</div>
                    </div>

                    {/* Teams */}
                    <div className="flex-1">
                      <div className="flex items-center gap-4">
                        {/* Home team */}
                        <div className="flex items-center gap-3 flex-1">
                          <div
                            className="w-4 h-4 rounded-full border"
                            style={{ backgroundColor: fixture.home_team.primary_color || "#666" }}
                          />
                          <span className="font-medium">{fixture.home_team.name}</span>
                        </div>

                        <span className="text-muted-foreground font-medium">vs</span>

                        {/* Away team */}
                        <div className="flex items-center gap-3 flex-1 justify-end">
                          <span className="font-medium">{fixture.away_team.name}</span>
                          <div
                            className="w-4 h-4 rounded-full border"
                            style={{ backgroundColor: fixture.away_team.primary_color || "#666" }}
                          />
                        </div>
                      </div>

                      {/* Venue & competition */}
                      <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {fixture.venue || "TBD"}
                        </div>
                        <div className="flex items-center gap-1">
                          <Trophy className="h-3 w-3" />
                          {fixture.tournament?.name || "Unknown"}
                        </div>
                        {fixture.matchday && (
                          <Badge variant="outline" className="text-xs">
                            Matchday {fixture.matchday}
                          </Badge>
                        )}
                        {fixture.round && (
                          <Badge variant="outline" className="text-xs">
                            {fixture.round}
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Status Badge */}
                    <div className="min-w-[100px] text-center">
                      {getStatusBadge(fixture.status)}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {fixture.status === "finished" ? (
                        <Button 
                          variant="outline" 
                          onClick={() => handleUploadToCloud(fixture)}
                          disabled={uploadingFixture === fixture.id}
                        >
                          {uploadingFixture === fixture.id ? (
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          ) : (
                            <Upload className="h-4 w-4 mr-2" />
                          )}
                          Upload to Cloud
                        </Button>
                      ) : isLoaded ? (
                        <Badge className="bg-green-500">
                          <Check className="h-4 w-4 mr-1" />
                          Loaded
                        </Badge>
                      ) : (
                        <Button onClick={() => setSelectedFixture(fixture)}>Load Fixture</Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Local Matches</h2>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={fetchLocalMatches} disabled={loadingLocal}>
              <RefreshCw className={`h-4 w-4 ${loadingLocal ? "animate-spin" : ""}`} />
            </Button>
            <Badge variant="secondary">{localMatches.length} created</Badge>
          </div>
        </div>

        {loadingLocal ? (
          <Card>
            <CardContent className="flex items-center justify-center py-10">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </CardContent>
          </Card>
        ) : localMatches.length === 0 ? (
          <Card>
            <CardContent className="py-10 text-center text-muted-foreground">
              No local matches found. Load a fixture from the cloud to create one.
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-3">
            {localMatches.map((local) => (
              <Card key={local.match.id}>
                <CardContent className="pt-6">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <div className="text-lg font-semibold">
                        {local.homeName}
                        <span className="mx-2 text-muted-foreground">vs</span>
                        {local.awayName}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {local.createdAt
                          ? `Created ${new Date(local.createdAt).toLocaleString("en-GB", {
                              dateStyle: "medium",
                              timeStyle: "short",
                            })}`
                          : "Created time unknown"}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Match ID: {local.match.id}
                        {local.match.fixture_id ? ` • Fixture: ${local.match.fixture_id}` : ""}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="uppercase">
                        {local.match.status.toUpperCase()}
                      </Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteLocalMatch(local)}
                        disabled={deletingMatchId === local.match.id}
                        className="border-destructive/50 text-destructive hover:bg-destructive/10"
                      >
                        {deletingMatchId === local.match.id ? (
                          <span className="flex items-center gap-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Deleting…
                          </span>
                        ) : (
                          <span className="flex items-center gap-2">
                            <Trash2 className="h-4 w-4" />
                            Delete
                          </span>
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* Load fixture confirmation dialog */}
      <Dialog open={!!selectedFixture} onOpenChange={() => setSelectedFixture(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Load Fixture from Cloud</DialogTitle>
            <DialogDescription>
              This will load the fixture data into the local database for match control.
            </DialogDescription>
          </DialogHeader>

          {selectedFixture && (
            <div className="py-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm text-muted-foreground">
                    {selectedFixture.tournament?.name || "Unknown Tournament"}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-center gap-6">
                    <div className="text-center">
                      <div
                        className="w-12 h-12 rounded-full border mx-auto mb-2"
                        style={{ backgroundColor: selectedFixture.home_team.primary_color || "#666" }}
                      />
                      <div className="font-medium">{selectedFixture.home_team.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {selectedFixture.home_team.short_name}
                      </div>
                    </div>
                    <div className="text-xl text-muted-foreground">vs</div>
                    <div className="text-center">
                      <div
                        className="w-12 h-12 rounded-full border mx-auto mb-2"
                        style={{ backgroundColor: selectedFixture.away_team.primary_color || "#666" }}
                      />
                      <div className="font-medium">{selectedFixture.away_team.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {selectedFixture.away_team.short_name}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center justify-center gap-4 mt-4 text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {selectedFixture.venue || "TBD"}
                    </div>
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {formatDate(selectedFixture.scheduled_date).date}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedFixture(null)} disabled={loadingFixture}>
              Cancel
            </Button>
            <Button onClick={handleLoadFixture} disabled={loadingFixture}>
              {loadingFixture && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Confirm & Load
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

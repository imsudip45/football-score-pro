"use client"

import type React from "react"
import { createContext, useContext, useReducer, useCallback, useEffect, useRef, useState } from "react"
import type {
  MatchState,
  ClockState,
  MatchEvent,
  PossessionState,
  MatchStats,
  PenaltyKick,
  Player,
  Team,
} from "./types"
import {
  matchApi,
  clockApi,
  eventsApi,
  statsApi,
  possessionApi,
  penaltiesApi,
  matchWebSocket,
  BASE_URL as BACKEND_BASE_URL,
  type ClockState as ApiClockState,
  type BackendMatchState,
} from "./api"


const normalizeAssetUrl = (url?: string | null): string => {
  if (!url) {
    return ""
  }
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url
  }
  if (url.startsWith("/")) {
    return `${BACKEND_BASE_URL}${url}`
  }
  return `${BACKEND_BASE_URL}/${url}`
}

// Default empty state - used before match is loaded from backend
const emptyTeam: Team = {
  id: "",
  name: "Team",
  logo_url: "",
  kit_color: "#333333",
  formation: "4-4-2",
}

const emptyPlayers: Player[] = []

const initialMatchState: MatchState = {
  match_id: "",
  status: "created",
  home_team: emptyTeam,
  away_team: emptyTeam,
  home_score: 0,
  away_score: 0,
  home_lineup: emptyPlayers,
  away_lineup: emptyPlayers,
  clock: {
    status: "stopped",
    period: "1H",
    real_elapsed_ms: 0,
    display_minute: 0,
    display_seconds: 0,
    stoppage_minutes: null,
    added_minutes: 0,
    formatted: "00:00",
  },
  possession: {
    home_pct: 50,
    away_pct: 50,
    current: null,
  },
  stats: {
    home: { shots: 0, shots_on_target: 0, corners: 0, fouls: 0, yellow_cards: 0, red_cards: 0 },
    away: { shots: 0, shots_on_target: 0, corners: 0, fouls: 0, yellow_cards: 0, red_cards: 0 },
  },
  events: [],
}

const createInitialMatchState = (): MatchState => ({
  ...initialMatchState,
  home_team: { ...initialMatchState.home_team },
  away_team: { ...initialMatchState.away_team },
  home_lineup: [],
  away_lineup: [],
  clock: { ...initialMatchState.clock },
  possession: { ...initialMatchState.possession },
  stats: {
    home: { ...initialMatchState.stats.home },
    away: { ...initialMatchState.stats.away },
  },
  events: [],
  penalty_shootout: undefined,
  venue: undefined,
  fixture_id: undefined,
})

type MatchAction =
  | { type: "SET_MATCH"; payload: MatchState }
  | { type: "UPDATE_CLOCK"; payload: ClockState }
  | { type: "ADD_EVENT"; payload: MatchEvent }
  | { type: "REMOVE_EVENT"; payload: number }
  | { type: "UPDATE_POSSESSION"; payload: PossessionState }
  | { type: "SET_STATS"; payload: MatchStats }
  | { type: "UPDATE_STATS"; payload: { team: "home" | "away"; stat: keyof MatchStats["home"]; delta: number } }
  | { type: "UPDATE_SCORE"; payload: { team: "home" | "away"; delta: number } }
  | { type: "SET_SCORE"; payload: { home: number; away: number } }
  | { type: "ADD_PENALTY_KICK"; payload: { team: "home" | "away"; kick: PenaltyKick } }
  | { type: "REMOVE_PENALTY_KICK"; payload: { team: "home" | "away"; kickId: number } }
  | { type: "SET_STATUS"; payload: MatchState["status"] }
  | { type: "SET_PENALTY_SHOOTOUT"; payload: MatchState["penalty_shootout"] }
  | { type: "SET_EVENTS"; payload: MatchEvent[] }

function getPeriodMinuteOffset(period: ClockState["period"]): number {
  switch (period) {
    case "1H":
      return 0
    case "HT":
      return 45
    case "2H":
      return 45
    case "ET1":
      return 90
    case "ET2":
      return 105
    case "PEN":
      return 120
    default:
      return 0
  }
}

function formatClock(minute: number, seconds: number, addedMinutes: number, period: ClockState["period"]): string {
  const baseMinute = minute.toString().padStart(2, "0")
  const sec = seconds.toString().padStart(2, "0")

  if (addedMinutes > 0 && (period === "1H" || period === "2H" || period === "ET1" || period === "ET2")) {
    const periodEndMinute = period === "1H" ? 45 : period === "2H" ? 90 : period === "ET1" ? 105 : 120
    if (minute >= periodEndMinute) {
      return `${periodEndMinute}+${minute - periodEndMinute + 1}:${sec}`
    }
  }

  return `${baseMinute}:${sec}`
}

// Convert backend clock state to our ClockState type
function convertBackendClock(apiClock: ApiClockState): ClockState {
  const apiClockAny = apiClock as unknown as { [key: string]: unknown }

  const rawMinute = apiClockAny.display_minute ?? apiClockAny.display_minutes ?? 0
  const rawSecond = apiClockAny.display_second ?? apiClockAny.display_seconds ?? 0
  const rawAdded = apiClockAny.added_time_minutes ?? apiClockAny.added_minutes ?? 0

  const minuteValue = Number(rawMinute)
  const secondValue = Number(rawSecond)
  const addedValue = Number(rawAdded)

  const minute = Number.isFinite(minuteValue) ? minuteValue : 0
  const seconds = Number.isFinite(secondValue) ? secondValue : 0
  const addedMinutes = Number.isFinite(addedValue) ? addedValue : 0

  const period = (apiClock.period as ClockState["period"]) || "1H"

  const formatted = formatClock(minute, seconds, addedMinutes, period)
  
  return {
    status: (apiClock.status as ClockState["status"]) || "stopped",
    period,
    real_elapsed_ms: Number.isFinite(Number(apiClock.real_elapsed_seconds))
      ? Number(apiClock.real_elapsed_seconds) * 1000
      : 0,
    display_minute: minute,
    display_seconds: seconds,
    stoppage_minutes: apiClock.is_added_time ? addedMinutes : null,
    added_minutes: addedMinutes,
    formatted,
  }
}

function convertBackendStats(stats: BackendMatchState["stats"] | null | undefined): MatchStats {
  return {
    home: {
      shots: stats?.home_shots ?? 0,
      shots_on_target: stats?.home_shots_on_target ?? 0,
      corners: stats?.home_corners ?? 0,
      fouls: stats?.home_fouls ?? 0,
      yellow_cards: stats?.home_yellow_cards ?? 0,
      red_cards: stats?.home_red_cards ?? 0,
    },
    away: {
      shots: stats?.away_shots ?? 0,
      shots_on_target: stats?.away_shots_on_target ?? 0,
      corners: stats?.away_corners ?? 0,
      fouls: stats?.away_fouls ?? 0,
      yellow_cards: stats?.away_yellow_cards ?? 0,
      red_cards: stats?.away_red_cards ?? 0,
    },
  }
}

function convertBackendPossession(possession: BackendMatchState["possession"] | null | undefined): PossessionState {
  return {
    home_pct: possession?.home_pct ?? 50,
    away_pct: possession?.away_pct ?? 50,
    current: (possession?.current_team as PossessionState["current"]) ?? null,
  }
}

function convertBackendPenaltyShootout(
  shootout: BackendMatchState["penalty_shootout"] | null | undefined,
): MatchState["penalty_shootout"] {
  if (!shootout) {
    return undefined
  }

  const mapKick = (kick: any) => ({
    id: kick?.id ?? 0,
    order: kick?.order ?? kick?.kick_order ?? 0,
    player_name: kick?.player_name ?? "",
    scored: Boolean(kick?.scored),
  })

  return {
    home_kicks: Array.isArray(shootout.home_kicks) ? shootout.home_kicks.map(mapKick) : [],
    away_kicks: Array.isArray(shootout.away_kicks) ? shootout.away_kicks.map(mapKick) : [],
    home_scored: shootout.home_scored ?? 0,
    away_scored: shootout.away_scored ?? 0,
    winner: shootout.winner ?? null,
  }
}

function normalizeMatchStatus(statusCandidate?: string | null): MatchState["status"] {
  const allowed: MatchState["status"][] = ["created", "live", "halftime", "finished"]
  if (!statusCandidate) {
    return "created"
  }
  if (allowed.includes(statusCandidate as MatchState["status"])) {
    return statusCandidate as MatchState["status"]
  }
  if (statusCandidate === "paused") {
    return "live"
  }
  if (statusCandidate === "abandoned") {
    return "finished"
  }
  return "created"
}

const VALID_EVENT_TYPES: MatchEvent["event_type"][] = [
  "goal",
  "own_goal",
  "yellow_card",
  "red_card",
  "second_yellow",
  "substitution",
  "penalty_scored",
  "penalty_missed",
]

function mapBackendEventType(eventType: string): MatchEvent["event_type"] {
  return VALID_EVENT_TYPES.includes(eventType as MatchEvent["event_type"])
    ? (eventType as MatchEvent["event_type"])
    : "goal"
}

function normalizeEventNumber(value: unknown): number | undefined {
  if (value === null || value === undefined) {
    return undefined
  }
  const num = Number(value)
  return Number.isFinite(num) ? num : undefined
}

function convertBackendEvents(events: BackendMatchState["events"] | null | undefined): MatchEvent[] {
  return (events ?? []).map((event) => ({
    id: event.id,
    event_type: mapBackendEventType(event.event_type),
    team: (event.team as "home" | "away") || "home",
    player_name: event.player_name,
    player_number: normalizeEventNumber(event.player_number),
    secondary_player_name: event.secondary_player_name ?? undefined,
    secondary_player_number: normalizeEventNumber(event.secondary_player_number),
    display_minute: event.display_minute,
    period: event.period,
    notes: event.notes ?? undefined,
    created_at: event.created_at,
    is_deleted: event.is_deleted ?? false,
  }))
}

function convertBackendEvent(event: any): MatchEvent | null {
  if (!event) {
    return null
  }
  return convertBackendEvents([event])[0] ?? null
}

function matchReducer(state: MatchState, action: MatchAction): MatchState {
  switch (action.type) {
    case "SET_MATCH":
      return action.payload

    case "UPDATE_CLOCK":
      return { ...state, clock: action.payload }

    case "SET_EVENTS":
      return { ...state, events: action.payload }

    case "SET_STATS":
      return { ...state, stats: action.payload }

    case "ADD_EVENT": {
      const event = action.payload
      const newState = { ...state, events: [...state.events, event] }

      // Update stats based on event type
      if (event.event_type === "yellow_card" || event.event_type === "second_yellow") {
        newState.stats = {
          ...newState.stats,
          [event.team]: {
            ...newState.stats[event.team],
            yellow_cards: newState.stats[event.team].yellow_cards + 1,
          },
        }
      }
      if (event.event_type === "red_card" || event.event_type === "second_yellow") {
        newState.stats = {
          ...newState.stats,
          [event.team]: {
            ...newState.stats[event.team],
            red_cards: newState.stats[event.team].red_cards + 1,
          },
        }
      }
      if (event.event_type === "goal" || event.event_type === "penalty_scored") {
        if (event.team === "home") {
          newState.home_score += 1
        } else {
          newState.away_score += 1
        }
      }
      if (event.event_type === "own_goal") {
        // Own goal goes to opposing team
        if (event.team === "home") {
          newState.away_score += 1
        } else {
          newState.home_score += 1
        }
      }

      return newState
    }

    case "REMOVE_EVENT": {
      const eventId = action.payload
      const event = state.events.find((e) => e.id === eventId)
      if (!event) return state

      const newState = { ...state, events: state.events.filter((e) => e.id !== eventId) }

      // Reverse stat changes
      if (event.event_type === "yellow_card" || event.event_type === "second_yellow") {
        newState.stats = {
          ...newState.stats,
          [event.team]: {
            ...newState.stats[event.team],
            yellow_cards: Math.max(0, newState.stats[event.team].yellow_cards - 1),
          },
        }
      }
      if (event.event_type === "red_card" || event.event_type === "second_yellow") {
        newState.stats = {
          ...newState.stats,
          [event.team]: {
            ...newState.stats[event.team],
            red_cards: Math.max(0, newState.stats[event.team].red_cards - 1),
          },
        }
      }
      if (event.event_type === "goal" || event.event_type === "penalty_scored") {
        if (event.team === "home") {
          newState.home_score = Math.max(0, newState.home_score - 1)
        } else {
          newState.away_score = Math.max(0, newState.away_score - 1)
        }
      }
      if (event.event_type === "own_goal") {
        if (event.team === "home") {
          newState.away_score = Math.max(0, newState.away_score - 1)
        } else {
          newState.home_score = Math.max(0, newState.home_score - 1)
        }
      }

      return newState
    }

    case "UPDATE_POSSESSION":
      return { ...state, possession: action.payload }

    case "UPDATE_STATS": {
      const { team, stat, delta } = action.payload
      return {
        ...state,
        stats: {
          ...state.stats,
          [team]: {
            ...state.stats[team],
            [stat]: Math.max(0, state.stats[team][stat] + delta),
          },
        },
      }
    }

    case "UPDATE_SCORE": {
      const { team, delta } = action.payload
      if (team === "home") {
        return { ...state, home_score: Math.max(0, state.home_score + delta) }
      }
      return { ...state, away_score: Math.max(0, state.away_score + delta) }
    }

    case "SET_SCORE":
      return {
        ...state,
        home_score: Math.max(0, action.payload.home),
        away_score: Math.max(0, action.payload.away),
      }

    case "ADD_PENALTY_KICK": {
      const { team, kick } = action.payload
      const currentShootout = state.penalty_shootout || {
        home_kicks: [],
        away_kicks: [],
        home_scored: 0,
        away_scored: 0,
        winner: null,
      }

      const newKicks =
        team === "home"
          ? {
              home_kicks: [...currentShootout.home_kicks, kick],
              away_kicks: currentShootout.away_kicks,
            }
          : {
              home_kicks: currentShootout.home_kicks,
              away_kicks: [...currentShootout.away_kicks, kick],
            }

      return {
        ...state,
        penalty_shootout: {
          ...newKicks,
          home_scored: newKicks.home_kicks.filter((k) => k.scored).length,
          away_scored: newKicks.away_kicks.filter((k) => k.scored).length,
          winner: null,
        },
      }
    }

    case "REMOVE_PENALTY_KICK": {
      const { team, kickId } = action.payload
      if (!state.penalty_shootout) return state

      const newKicks =
        team === "home"
          ? {
              home_kicks: state.penalty_shootout.home_kicks.filter((k) => k.id !== kickId),
              away_kicks: state.penalty_shootout.away_kicks,
            }
          : {
              home_kicks: state.penalty_shootout.home_kicks,
              away_kicks: state.penalty_shootout.away_kicks.filter((k) => k.id !== kickId),
            }

      return {
        ...state,
        penalty_shootout: {
          ...newKicks,
          home_scored: newKicks.home_kicks.filter((k) => k.scored).length,
          away_scored: newKicks.away_kicks.filter((k) => k.scored).length,
          winner: null,
        },
      }
    }

    case "SET_PENALTY_SHOOTOUT":
      return { ...state, penalty_shootout: action.payload }

    case "SET_STATUS":
      return { ...state, status: action.payload }

    default:
      return state
  }
}

interface MatchContextType {
  match: MatchState
  dispatch: React.Dispatch<MatchAction>
  hasActiveMatch: boolean
  isConnected: boolean
  isLoading: boolean
  error: string | null
  
  // Match lifecycle
  loadMatch: (matchId: string) => Promise<void>
  refreshMatch: () => Promise<void>
  
  // Clock controls (now async - call backend)
  startClock: () => Promise<void>
  pauseClock: () => Promise<void>
  stopClock: () => Promise<void>
  resumeClock: () => Promise<void>
  nextPeriod: () => Promise<void>
  setAddedTime: (minutes: number) => Promise<void>
  
  // Events (now async - call backend)
  addEvent: (event: Omit<MatchEvent, "id" | "created_at" | "display_minute" | "period">) => Promise<void>
  removeEvent: (eventId: number) => Promise<void>
  
  // Possession (now async - call backend)
  updatePossession: (team: "home" | "away" | null) => Promise<void>
  
  // Stats (now async - call backend)
  updateStat: (team: "home" | "away", stat: keyof MatchStats["home"], delta: number) => Promise<void>
  
  // Penalty shootout (now async - call backend)
  addPenaltyKick: (team: "home" | "away", playerName: string, scored: boolean) => Promise<void>
  removePenaltyKick: (team: "home" | "away", kickId: number) => Promise<void>
  
  // Match end
  endMatch: () => Promise<boolean>
  deleteMatch: (matchId?: string) => Promise<boolean>
}

const MatchContext = createContext<MatchContextType | null>(null)

export function MatchProvider({ children }: { children: React.ReactNode }) {
  const [match, dispatch] = useReducer(matchReducer, initialMatchState)
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const matchIdRef = useRef<string | null>(null)
  const activeMatchPollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const isFetchingActiveRef = useRef(false)
  const matchStateRef = useRef(match)

  useEffect(() => {
    matchStateRef.current = match
  }, [match])

  // Setup WebSocket listeners
  useEffect(() => {
    const unsubClock = matchWebSocket.on("clock", (data) => {
      const clockData = data as ApiClockState
      dispatch({ type: "UPDATE_CLOCK", payload: convertBackendClock(clockData) })
    })

    const unsubState = matchWebSocket.on("state", (data) => {
      const stateData = data as BackendMatchState

      if (stateData.clock) {
        dispatch({ type: "UPDATE_CLOCK", payload: convertBackendClock(stateData.clock as ApiClockState) })
      }

      if (stateData.events) {
        dispatch({ type: "SET_EVENTS", payload: convertBackendEvents(stateData.events) })
      }

      if (stateData.match) {
        dispatch({
          type: "SET_SCORE",
          payload: {
            home: Number(stateData.match.home_score) || 0,
            away: Number(stateData.match.away_score) || 0,
          },
        })
        dispatch({ type: "SET_STATUS", payload: normalizeMatchStatus(stateData.match.status as string) })
      }

      if ("possession" in stateData) {
        dispatch({ type: "UPDATE_POSSESSION", payload: convertBackendPossession(stateData.possession) })
      }

      if ("stats" in stateData) {
        dispatch({ type: "SET_STATS", payload: convertBackendStats(stateData.stats) })
      }

      if ("penalty_shootout" in stateData) {
        dispatch({ type: "SET_PENALTY_SHOOTOUT", payload: convertBackendPenaltyShootout(stateData.penalty_shootout) })
      }
    })

    const unsubEvent = matchWebSocket.on("event", (data) => {
      const eventData = convertBackendEvent(data)
      if (eventData) {
        dispatch({ type: "ADD_EVENT", payload: eventData })
      }
    })

    const unsubScore = matchWebSocket.on("score", (data) => {
      const scoreData = data as { home_score?: number; away_score?: number }
      dispatch({
        type: "SET_SCORE",
        payload: {
          home: typeof scoreData.home_score === "number" ? scoreData.home_score : matchStateRef.current.home_score,
          away: typeof scoreData.away_score === "number" ? scoreData.away_score : matchStateRef.current.away_score,
        },
      })
    })

    const unsubPossession = matchWebSocket.on("possession", (data) => {
      dispatch({ type: "UPDATE_POSSESSION", payload: convertBackendPossession(data as BackendMatchState["possession"]) })
    })

    const unsubStats = matchWebSocket.on("stats", (data) => {
      dispatch({ type: "SET_STATS", payload: convertBackendStats(data as BackendMatchState["stats"]) })
    })

    const unsubPenalty = matchWebSocket.on("penalty", (data) => {
      dispatch({ type: "SET_PENALTY_SHOOTOUT", payload: convertBackendPenaltyShootout(data as BackendMatchState["penalty_shootout"]) })
    })

    const unsubMatchStatus = matchWebSocket.on("match_status", (data) => {
      const statusData = data as { status?: string; period?: string }
      if (statusData.status) {
        dispatch({ type: "SET_STATUS", payload: normalizeMatchStatus(statusData.status) })
      }
      if (statusData.period) {
        const currentClock = matchStateRef.current.clock
        dispatch({
          type: "UPDATE_CLOCK",
          payload: {
            ...currentClock,
            period: (statusData.period as ClockState["period"]) || currentClock.period,
          },
        })
      }
    })

    return () => {
      unsubClock()
      unsubState()
      unsubEvent()
      unsubScore()
      unsubPossession()
      unsubStats()
      unsubPenalty()
      unsubMatchStatus()
      matchWebSocket.disconnect()
    }
  }, [])

  // Load match from backend
  const loadMatch = useCallback(async (matchId: string) => {
    setIsLoading(true)
    setError(null)
    
    try {
      const result = await matchApi.getMatchState(matchId)
      if (result.error) {
        setError(result.error)
        return
      }
      
      if (result.data) {
        // Convert backend match state to our format
        const backendMatchState = result.data as BackendMatchState
        const backendMatch = backendMatchState.match

        const mapTeam = (
          teamData: BackendMatchState["home_team"],
          fallbackId: string,
          defaultName: string,
          formation?: string | null
        ): Team => ({
          id: (teamData?.id as string) || fallbackId || "",
          name:
            teamData?.name ||
            teamData?.short_name ||
            teamData?.full_name ||
            defaultName,
          logo_url: normalizeAssetUrl(
            (teamData?.logo_url as string | undefined) ||
              (teamData?.logo_path as string | undefined) ||
              ((teamData as Record<string, unknown> | undefined)?.logo as string | undefined)
          ),
          kit_color: teamData?.kit_color || teamData?.primary_color || "#333333",
          formation: formation || teamData?.formation || "4-4-2",
        })

        const convertPlayers = (
          players: BackendMatchState["home_lineup"] | null | undefined,
          side: "home" | "away"
        ): Player[] => (players ?? []).map((p, index) => ({
            id: p.player_id || `${side}-${index}`,
            name: p.name || p.short_name || `Player ${index + 1}`,
            jersey_number: p.jersey_number ?? 0,
            position: p.position_in_formation || "N/A",
          }))

        const homeTeam = mapTeam(backendMatchState.home_team, backendMatch.home_team_id, "Home Team", backendMatch.home_formation)
        const awayTeam = mapTeam(backendMatchState.away_team, backendMatch.away_team_id, "Away Team", backendMatch.away_formation)

        const homePlayers = convertPlayers(backendMatchState.home_lineup, "home")
        const awayPlayers = convertPlayers(backendMatchState.away_lineup, "away")

        const clockState = backendMatchState.clock
          ? convertBackendClock(backendMatchState.clock as ApiClockState)
          : { ...initialMatchState.clock }

        const convertedMatchStats = convertBackendStats(backendMatchState.stats)
        const convertedPossession = convertBackendPossession(backendMatchState.possession)

        const convertedEvents = convertBackendEvents(backendMatchState.events)

        const penaltyShootout = convertBackendPenaltyShootout(backendMatchState.penalty_shootout)

        const status = normalizeMatchStatus(backendMatch.status as string)
        const convertedMatch: MatchState = {
          match_id: backendMatch.id,
          status,
          home_team: homeTeam,
          away_team: awayTeam,
          home_score: backendMatch.home_score,
          away_score: backendMatch.away_score,
          home_lineup: homePlayers,
          away_lineup: awayPlayers,
          clock: clockState,
          possession: convertedPossession,
          stats: convertedMatchStats,
          events: convertedEvents,
          penalty_shootout: penaltyShootout,
          venue: backendMatch.venue || undefined,
          fixture_id: backendMatch.fixture_id || undefined,
        }
        dispatch({ type: "SET_MATCH", payload: convertedMatch })
        matchIdRef.current = backendMatch.id

        // Connect WebSocket
        matchWebSocket.connect(backendMatch.id)
        setIsConnected(true)
      }
    } catch (err) {
      setError(String(err))
    } finally {
      setIsLoading(false)
    }
  }, [])

  const refreshMatch = useCallback(async () => {
    if (matchIdRef.current) {
      await loadMatch(matchIdRef.current)
    }
  }, [loadMatch])

  useEffect(() => {
    let isMounted = true

    const fetchActiveMatch = async () => {
      if (isFetchingActiveRef.current || !isMounted) {
        return
      }

      isFetchingActiveRef.current = true
      try {
        const active = await matchApi.getActiveMatch()
        if (!isMounted) {
          return
        }

        if (active.data && active.data.id) {
          const activeId = active.data.id
          if (matchIdRef.current !== activeId) {
            await loadMatch(activeId)
          }
        }
      } catch (err) {
        console.error("Failed to load active match", err)
      } finally {
        isFetchingActiveRef.current = false
      }
    }

    fetchActiveMatch()

    activeMatchPollRef.current = setInterval(() => {
      if (!matchIdRef.current) {
        void fetchActiveMatch()
      }
    }, 5000)

    return () => {
      isMounted = false
      if (activeMatchPollRef.current) {
        clearInterval(activeMatchPollRef.current)
        activeMatchPollRef.current = null
      }
    }
  }, [loadMatch])

  // Clock controls
  const startClock = useCallback(async () => {
    if (!matchIdRef.current) return
    const result = await clockApi.startClock(matchIdRef.current)
    if (result.data) {
      dispatch({ type: "UPDATE_CLOCK", payload: convertBackendClock(result.data) })
    }
  }, [])

  const pauseClock = useCallback(async () => {
    if (!matchIdRef.current) return
    const result = await clockApi.pauseClock(matchIdRef.current)
    if (result.data) {
      dispatch({ type: "UPDATE_CLOCK", payload: convertBackendClock(result.data) })
    }
  }, [])

  const resumeClock = useCallback(async () => {
    if (!matchIdRef.current) return
    const result = await clockApi.resumeClock(matchIdRef.current)
    if (result.data) {
      dispatch({ type: "UPDATE_CLOCK", payload: convertBackendClock(result.data) })
    }
  }, [])

  const stopClock = useCallback(async () => {
    if (!matchIdRef.current) return
    const result = await clockApi.stopClock(matchIdRef.current)
    if (result.data) {
      dispatch({ type: "UPDATE_CLOCK", payload: convertBackendClock(result.data) })
    }
  }, [])

  const nextPeriod = useCallback(async () => {
    if (!matchIdRef.current) return
    const result = await clockApi.nextPeriod(matchIdRef.current)
    if (result.data) {
      dispatch({ type: "UPDATE_CLOCK", payload: convertBackendClock(result.data) })
    }
  }, [])

  const setAddedTime = useCallback(async (minutes: number) => {
    if (!matchIdRef.current) return
    const result = await clockApi.setAddedTime(matchIdRef.current, minutes)
    if (result.data) {
      dispatch({ type: "UPDATE_CLOCK", payload: convertBackendClock(result.data) })
    }
  }, [])

  // Events
  const addEvent = useCallback(async (event: Omit<MatchEvent, "id" | "created_at" | "display_minute" | "period">) => {
    if (!matchIdRef.current) return
    const result = await eventsApi.addEvent(matchIdRef.current, {
      event_type: event.event_type,
      team: event.team,
      player_name: event.player_name,
      player_number: event.player_number,
      secondary_player_name: event.secondary_player_name,
      secondary_player_number: event.secondary_player_number,
      notes: event.notes,
    })
    if (result.data) {
      dispatch({ type: "ADD_EVENT", payload: result.data as unknown as MatchEvent })
    }
  }, [])

  const removeEvent = useCallback(async (eventId: number) => {
    if (!matchIdRef.current) return
    const result = await eventsApi.undoEvent(matchIdRef.current, eventId)
    if (result.success) {
      dispatch({ type: "REMOVE_EVENT", payload: eventId })
    }
  }, [])

  // Possession
  const updatePossession = useCallback(async (team: "home" | "away" | null) => {
    if (!matchIdRef.current) return
    
    let newPossession: PossessionState
    if (team === "home") {
      newPossession = {
        home_pct: Math.min(100, match.possession.home_pct + 1),
        away_pct: Math.max(0, match.possession.away_pct - 1),
        current: "home",
      }
    } else if (team === "away") {
      newPossession = {
        home_pct: Math.max(0, match.possession.home_pct - 1),
        away_pct: Math.min(100, match.possession.away_pct + 1),
        current: "away",
      }
    } else {
      newPossession = { home_pct: 50, away_pct: 50, current: null }
    }
    
    const result = await possessionApi.updatePossession(matchIdRef.current, {
      current_team: team,
      home_pct: newPossession.home_pct,
      away_pct: newPossession.away_pct,
    })
    
    if (result.data) {
      dispatch({ type: "UPDATE_POSSESSION", payload: newPossession })
    }
  }, [match.possession])

  // Stats
  const updateStat = useCallback(async (team: "home" | "away", stat: keyof MatchStats["home"], delta: number) => {
    if (!matchIdRef.current) return
    
    // Map frontend stat names to backend stat names
    const statMap: Record<string, string> = {
      shots: 'shots',
      shots_on_target: 'shots_on_target',
      corners: 'corners',
      fouls: 'fouls',
      yellow_cards: 'yellow_cards',
      red_cards: 'red_cards',
    }
    
    const result = await statsApi.updateStat(matchIdRef.current, team, statMap[stat] || stat, delta)
    if (result.data) {
      dispatch({ type: "UPDATE_STATS", payload: { team, stat, delta } })
    }
  }, [])

  // Penalty shootout
  const addPenaltyKick = useCallback(async (team: "home" | "away", playerName: string, scored: boolean) => {
    if (!matchIdRef.current) return
    const result = await penaltiesApi.addKick(matchIdRef.current, team, playerName, scored)
    if (result.data) {
      const kick = result.data
      dispatch({
        type: "ADD_PENALTY_KICK",
        payload: {
          team,
          kick: {
            id: kick.id,
            order: kick.order,
            player_name: kick.player_name,
            scored: kick.scored,
          },
        },
      })
    }
  }, [])

  const removePenaltyKick = useCallback(async (team: "home" | "away", kickId: number) => {
    if (!matchIdRef.current) return
    const result = await penaltiesApi.undoKick(matchIdRef.current, kickId)
    if (result.success) {
      dispatch({ type: "REMOVE_PENALTY_KICK", payload: { team, kickId } })
    }
  }, [])

  const endMatch = useCallback(async (): Promise<boolean> => {
    if (!matchIdRef.current) {
      return false
    }

    try {
      await stopClock()
      const result = await matchApi.endMatch(matchIdRef.current)

      if (result.data) {
        const status = (result.data.status as MatchState["status"]) || "finished"
        dispatch({ type: "SET_STATUS", payload: status })
        setError(null)
        return true
      }

      if (result.error) {
        setError(result.error)
      }
    } catch (err) {
      setError(String(err))
    }

    return false
  }, [stopClock])

  const deleteMatch = useCallback(async (targetMatchId?: string): Promise<boolean> => {
    const id = targetMatchId ?? matchIdRef.current
    if (!id) {
      return false
    }

    try {
      const result = await matchApi.deleteMatch(id)

      if (!result.success) {
        if (result.error) {
          setError(result.error)
        }
        return false
      }

      if (matchIdRef.current === id) {
        dispatch({ type: "SET_MATCH", payload: createInitialMatchState() })
        matchIdRef.current = null
        if (isConnected) {
          matchWebSocket.disconnect()
          setIsConnected(false)
        }
      }

      setError(null)
      return true
    } catch (err) {
      setError(String(err))
      return false
    }
  }, [isConnected])

  const hasActiveMatch = match.status !== "finished" && match.match_id !== ""

  useEffect(() => {
    if (match.match_id && match.status === "finished") {
      matchIdRef.current = null
      if (isConnected) {
        matchWebSocket.disconnect()
        setIsConnected(false)
      }
    }
  }, [isConnected, match.match_id, match.status])

  return (
    <MatchContext.Provider
      value={{
        match,
        dispatch,
        hasActiveMatch,
        isConnected,
        isLoading,
        error,
        loadMatch,
        refreshMatch,
        startClock,
        pauseClock,
        stopClock,
        resumeClock,
        nextPeriod,
        setAddedTime,
        addEvent,
        removeEvent,
        updatePossession,
        updateStat,
        addPenaltyKick,
        removePenaltyKick,
        endMatch,
        deleteMatch,
      }}
    >
      {children}
    </MatchContext.Provider>
  )
}

export function useMatch() {
  const context = useContext(MatchContext)
  if (!context) {
    throw new Error("useMatch must be used within a MatchProvider")
  }
  return context
}

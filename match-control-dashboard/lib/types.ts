// Core types for the football match control dashboard

export interface Team {
  id: string
  name: string
  logo_url?: string
  kit_color: string
  formation: string
}

export interface Player {
  id: string
  name: string
  jersey_number: number
  position: string
}

export interface ClockState {
  status: "stopped" | "running" | "paused"
  period: "1H" | "HT" | "2H" | "ET1" | "ET2" | "PEN"
  real_elapsed_ms: number
  display_minute: number
  display_seconds: number
  stoppage_minutes: number | null
  added_minutes: number
  formatted: string
}

export interface MatchStats {
  home: TeamStats
  away: TeamStats
}

export interface TeamStats {
  shots: number
  shots_on_target: number
  corners: number
  fouls: number
  yellow_cards: number
  red_cards: number
}

export interface PossessionState {
  home_pct: number
  away_pct: number
  current: "home" | "away" | null
}

export interface MatchEvent {
  id: number
  event_type:
    | "goal"
    | "own_goal"
    | "yellow_card"
    | "red_card"
    | "second_yellow"
    | "substitution"
    | "penalty_scored"
    | "penalty_missed"
  team: "home" | "away"
  player_name?: string
  player_number?: number
  secondary_player_name?: string
  secondary_player_number?: number
  display_minute: number
  period: string
  notes?: string
  created_at: string
}

export interface PenaltyKick {
  id: number
  order: number
  player_name: string
  scored: boolean
}

export interface PenaltyShootout {
  home_kicks: PenaltyKick[]
  away_kicks: PenaltyKick[]
  home_scored: number
  away_scored: number
  winner: "home" | "away" | null
}

export interface MatchState {
  match_id: string
  status: "created" | "live" | "halftime" | "finished"
  home_team: Team
  away_team: Team
  home_score: number
  away_score: number
  home_lineup: Player[]
  away_lineup: Player[]
  clock: ClockState
  possession: PossessionState
  stats: MatchStats
  events: MatchEvent[]
  penalty_shootout?: PenaltyShootout
  venue?: string
  fixture_id?: string
}

export interface Fixture {
  id: string
  date: string
  home_team: Team
  away_team: Team
  venue: string
  competition: string
}

export type EventType = MatchEvent["event_type"]

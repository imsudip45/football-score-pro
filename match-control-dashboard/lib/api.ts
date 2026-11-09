/**
 * Backend API Client for Match Control Dashboard
 * Connects to FastAPI backend at localhost:8000
 */

// Set NEXT_PUBLIC_API_URL to point the dashboard at a different match API
export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApiResponse<T> {
  data: T | null;
  error: string | null;
}

async function apiGet<T>(path: string): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (!response.ok) {
      const error = await response.text();
      return { data: null, error: `${response.status}: ${error}` };
    }
    
    const data = await response.json();
    return { data, error: null };
  } catch (err) {
    return { data: null, error: String(err) };
  }
}

async function apiPost<T>(path: string, body?: Record<string, unknown>): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    
    if (!response.ok) {
      const error = await response.text();
      return { data: null, error: `${response.status}: ${error}` };
    }
    
    const data = await response.json();
    return { data, error: null };
  } catch (err) {
    return { data: null, error: String(err) };
  }
}

async function apiDelete(path: string): Promise<{ success: boolean; error: string | null }> {
  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (!response.ok) {
      const error = await response.text();
      return { success: false, error: `${response.status}: ${error}` };
    }
    
    return { success: true, error: null };
  } catch (err) {
    return { success: false, error: String(err) };
  }
}

// ============ Types ============

export interface Team {
  id: string;
  name: string;
  short_name: string;
  logo_path?: string;
  primary_color?: string;
  secondary_color?: string;
}

export interface Player {
  id: string;
  name: string;
  number: number;
  position: string;
  is_captain?: boolean;
  is_starting?: boolean;
}

export interface ClockState {
  status: 'stopped' | 'running' | 'paused';
  period: string;
  display_minute: number;
  display_second: number;
  real_elapsed_seconds: number;
  added_time_minutes: number;
  is_added_time: boolean;
}

export interface MatchEvent {
  id: number;
  event_type: string;
  team: 'home' | 'away';
  player_name?: string;
  player_number?: number;
  secondary_player_name?: string;
  secondary_player_number?: number;
  display_minute: number;
  period: string;
  notes?: string;
  created_at: string;
  is_deleted?: boolean;
}

export interface MatchStats {
  home: {
    shots: number;
    shots_on_target: number;
    corners: number;
    fouls: number;
    offsides: number;
    free_kicks: number;
  };
  away: {
    shots: number;
    shots_on_target: number;
    corners: number;
    fouls: number;
    offsides: number;
    free_kicks: number;
  };
}

export interface PossessionState {
  home_pct: number;
  away_pct: number;
  current_team: 'home' | 'away' | null;
  kickoff_team: 'home' | 'away' | null;
}

export interface PenaltyKick {
  id: number;
  order: number;
  team: 'home' | 'away';
  player_name: string;
  scored: boolean;
}

export interface PenaltyShootout {
  is_active: boolean;
  home_scored: number;
  away_scored: number;
  home_kicks: PenaltyKick[];
  away_kicks: PenaltyKick[];
  current_round: number;
  first_team: 'home' | 'away';
  winner: 'home' | 'away' | null;
}

export interface BackendLineupPlayer {
  player_id: string;
  team?: 'home' | 'away' | null;
  is_starting: boolean;
  is_captain: boolean;
  position_in_formation?: string | null;
  formation_x?: number | null;
  formation_y?: number | null;
  jersey_number?: number | null;
  name?: string | null;
  short_name?: string | null;
}

export interface BackendMatchStatsRow {
  home_shots: number;
  away_shots: number;
  home_shots_on_target: number;
  away_shots_on_target: number;
  home_corners: number;
  away_corners: number;
  home_fouls: number;
  away_fouls: number;
  home_offsides: number;
  away_offsides: number;
  home_yellow_cards?: number;
  away_yellow_cards?: number;
  home_red_cards?: number;
  away_red_cards?: number;
}

export interface BackendPossession {
  home_ms: number;
  away_ms: number;
  home_pct: number;
  away_pct: number;
  current_team?: 'home' | 'away' | null;
}

export interface BackendMatchState {
  match: BackendMatch;
  home_team?: Partial<Team> & {
    short_name?: string;
    full_name?: string;
    logo_path?: string;
    logo_url?: string;
    primary_color?: string;
    secondary_color?: string;
    kit_color?: string;
    formation?: string;
  } | null;
  away_team?: Partial<Team> & {
    short_name?: string;
    full_name?: string;
    logo_path?: string;
    logo_url?: string;
    primary_color?: string;
    secondary_color?: string;
    kit_color?: string;
    formation?: string;
  } | null;
  home_lineup: BackendLineupPlayer[];
  away_lineup: BackendLineupPlayer[];
  clock?: ClockState | null;
  possession?: BackendPossession | null;
  stats?: BackendMatchStatsRow | null;
  events: MatchEvent[];
  penalty_shootout?: {
    home_kicks: any[];
    away_kicks: any[];
    home_scored: number;
    away_scored: number;
    winner?: 'home' | 'away' | null;
  } | null;
}

export interface BackendMatch {
  id: string;
  fixture_id?: string | null;
  home_team_id: string;
  away_team_id: string;
  home_formation?: string | null;
  away_formation?: string | null;
  home_kit_id?: string | null;
  away_kit_id?: string | null;
  status: 'created' | 'live' | 'halftime' | 'finished' | 'abandoned';
  current_period: string;
  home_score: number;
  away_score: number;
  winner?: string | null;
  venue?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

// ============ Match API ============

export const matchApi = {
  async getMatch(matchId: string) {
    return apiGet<BackendMatch>(`/matches/${matchId}`);
  },

  async getMatchState(matchId: string) {
    return apiGet<BackendMatchState>(`/matches/${matchId}/state`);
  },

  async listMatches(status?: string) {
    const path = status ? `/matches?status=${status}` : '/matches';
    return apiGet<BackendMatch[]>(path);
  },

  async createMatch(data: {
    home_team: Partial<Team>;
    away_team: Partial<Team>;
    home_lineup: Partial<Player>[];
    away_lineup: Partial<Player>[];
    fixture_id?: string;
    venue?: string;
    competition?: string;
  }) {
    return apiPost<BackendMatch>('/matches', data);
  },

  async getSnapshot(matchId: string) {
    return apiGet<BackendMatchState>(`/matches/${matchId}/snapshot`);
  },

  async endMatch(matchId: string) {
    return apiPost<BackendMatch>(`/matches/${matchId}/finish`);
  },

  async resetMatch(matchId: string) {
    return apiPost<BackendMatch>(`/matches/${matchId}/reset`);
  },

  async getActiveMatch() {
    return apiGet<BackendMatch | null>('/matches/active');
  },

  async deleteMatch(matchId: string) {
    return apiDelete(`/matches/${matchId}`);
  },
};

// ============ Clock API ============

export const clockApi = {
  async getClock(matchId: string) {
    return apiGet<ClockState>(`/matches/${matchId}/clock`);
  },

  async startClock(matchId: string) {
    return apiPost<ClockState>(`/matches/${matchId}/clock/start`);
  },

  async pauseClock(matchId: string) {
    return apiPost<ClockState>(`/matches/${matchId}/clock/pause`);
  },

  async resumeClock(matchId: string) {
    return apiPost<ClockState>(`/matches/${matchId}/clock/resume`);
  },

  async stopClock(matchId: string) {
    return apiPost<ClockState>(`/matches/${matchId}/clock/stop`);
  },

  async setTime(matchId: string, minutes: number, seconds: number = 0) {
    return apiPost<ClockState>(`/matches/${matchId}/clock/set-time`, { minutes, seconds });
  },

  async setAddedTime(matchId: string, minutes: number) {
    return apiPost<ClockState>(`/matches/${matchId}/clock/added-time`, { minutes });
  },

  async nextPeriod(matchId: string) {
    return apiPost<ClockState>(`/matches/${matchId}/clock/next-period`);
  },

  async setPeriod(matchId: string, period: string) {
    return apiPost<ClockState>(`/matches/${matchId}/clock/set-period`, { period });
  },
};

// ============ Events API ============

export const eventsApi = {
  async getEvents(matchId: string, includeDeleted: boolean = false) {
    const path = includeDeleted 
      ? `/matches/${matchId}/events?include_deleted=true`
      : `/matches/${matchId}/events`;
    return apiGet<MatchEvent[]>(path);
  },

  async addEvent(matchId: string, data: {
    event_type: string;
    team: 'home' | 'away';
    player_name?: string;
    player_number?: number;
    secondary_player_name?: string;
    secondary_player_number?: number;
    notes?: string;
  }) {
    return apiPost<MatchEvent>(`/matches/${matchId}/events`, data);
  },

  async undoEvent(matchId: string, eventId: number) {
    return apiDelete(`/matches/${matchId}/events/${eventId}`);
  },

  // Convenience methods
  async addGoal(matchId: string, team: 'home' | 'away', playerName?: string, playerNumber?: number, assistName?: string, assistNumber?: number) {
    return this.addEvent(matchId, {
      event_type: 'goal',
      team,
      player_name: playerName,
      player_number: playerNumber,
      secondary_player_name: assistName,
      secondary_player_number: assistNumber,
    });
  },

  async addOwnGoal(matchId: string, team: 'home' | 'away', playerName?: string, playerNumber?: number) {
    return this.addEvent(matchId, {
      event_type: 'own_goal',
      team,
      player_name: playerName,
      player_number: playerNumber,
    });
  },

  async addYellowCard(matchId: string, team: 'home' | 'away', playerName?: string, playerNumber?: number, reason?: string) {
    return this.addEvent(matchId, {
      event_type: 'yellow_card',
      team,
      player_name: playerName,
      player_number: playerNumber,
      notes: reason,
    });
  },

  async addRedCard(matchId: string, team: 'home' | 'away', playerName?: string, playerNumber?: number, reason?: string) {
    return this.addEvent(matchId, {
      event_type: 'red_card',
      team,
      player_name: playerName,
      player_number: playerNumber,
      notes: reason,
    });
  },

  async addSubstitution(matchId: string, team: 'home' | 'away', playerOutName?: string, playerOutNumber?: number, playerInName?: string, playerInNumber?: number) {
    return this.addEvent(matchId, {
      event_type: 'substitution',
      team,
      player_name: playerOutName,
      player_number: playerOutNumber,
      secondary_player_name: playerInName,
      secondary_player_number: playerInNumber,
    });
  },
};

// ============ Stats API ============

export const statsApi = {
  async getStats(matchId: string) {
    return apiGet<MatchStats>(`/matches/${matchId}/stats`);
  },

  async updateStat(matchId: string, team: 'home' | 'away', stat: string, delta: number) {
    return apiPost<MatchStats>(`/matches/${matchId}/stats`, { team, stat, delta });
  },

  // Convenience methods
  async incrementShots(matchId: string, team: 'home' | 'away', onTarget: boolean = false) {
    const stat = onTarget ? 'shots_on_target' : 'shots';
    return this.updateStat(matchId, team, stat, 1);
  },

  async incrementCorners(matchId: string, team: 'home' | 'away') {
    return this.updateStat(matchId, team, 'corners', 1);
  },

  async incrementFouls(matchId: string, team: 'home' | 'away') {
    return this.updateStat(matchId, team, 'fouls', 1);
  },

  async incrementOffsides(matchId: string, team: 'home' | 'away') {
    return this.updateStat(matchId, team, 'offsides', 1);
  },
};

// ============ Possession API ============

export const possessionApi = {
  async getPossession(matchId: string) {
    return apiGet<PossessionState>(`/matches/${matchId}/possession`);
  },

  async updatePossession(matchId: string, data: {
    current_team?: 'home' | 'away' | null;
    home_pct?: number;
    away_pct?: number;
  }) {
    return apiPost<PossessionState>(`/matches/${matchId}/possession`, data);
  },

  async setKickoffTeam(matchId: string, team: 'home' | 'away') {
    return apiPost<PossessionState>(`/matches/${matchId}/possession/kickoff`, { team });
  },
};

// ============ Penalty Shootout API ============

export const penaltiesApi = {
  async getPenalties(matchId: string) {
    return apiGet<PenaltyShootout>(`/matches/${matchId}/penalties`);
  },

  async startShootout(matchId: string, firstTeam: 'home' | 'away') {
    return apiPost<PenaltyShootout>(`/matches/${matchId}/penalties/start`, { first_team: firstTeam });
  },

  async addKick(matchId: string, team: 'home' | 'away', playerName: string, scored: boolean) {
    return apiPost<PenaltyKick>(`/matches/${matchId}/penalties/kick`, {
      team,
      player_name: playerName,
      scored,
    });
  },

  async undoKick(matchId: string, kickId: number) {
    return apiDelete(`/matches/${matchId}/penalties/${kickId}`);
  },
};

// ============ WebSocket ============

export type WebSocketMessageType =
  | 'clock'
  | 'state'
  | 'event'
  | 'score'
  | 'possession'
  | 'stats'
  | 'penalty'
  | 'match_status';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  data: unknown;
}

export class MatchWebSocket {
  private ws: WebSocket | null = null;
  private matchId: string | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private listeners: Map<WebSocketMessageType, Set<(data: unknown) => void>> = new Map();

  constructor() {
    const messageTypes: WebSocketMessageType[] = [
      'clock',
      'state',
      'event',
      'score',
      'possession',
      'stats',
      'penalty',
      'match_status',
    ];

    messageTypes.forEach((type) => {
      this.listeners.set(type, new Set());
    });
  }

  connect(matchId: string) {
    this.matchId = matchId;
    const wsUrl = BASE_URL.replace('http', 'ws');
    this.ws = new WebSocket(`${wsUrl}/ws/matches/${matchId}`);

    this.ws.onopen = () => {
      console.log(`[MatchWS] Connected to match ${matchId}`);
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.ws.onclose = () => {
      console.log(`[MatchWS] Disconnected from match ${matchId}`);
      this.scheduleReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('[MatchWS] WebSocket error:', error);
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        const listeners = this.listeners.get(message.type);
        if (listeners && listeners.size > 0) {
          listeners.forEach((callback) => callback(message.data));
        } else if (!this.listeners.has(message.type)) {
          console.debug('[MatchWS] Ignoring unhandled message type:', message.type);
        }
      } catch (err) {
        console.error('[MatchWS] Failed to parse message:', err);
      }
    };
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.matchId = null;
  }

  private scheduleReconnect() {
    if (this.matchId && !this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => {
        if (this.matchId) {
          console.log('[MatchWS] Attempting reconnect...');
          this.connect(this.matchId);
        }
      }, 2000);
    }
  }

  on(type: WebSocketMessageType, callback: (data: unknown) => void) {
    this.listeners.get(type)?.add(callback);
    return () => this.off(type, callback);
  }

  off(type: WebSocketMessageType, callback: (data: unknown) => void) {
    this.listeners.get(type)?.delete(callback);
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Export a singleton WebSocket instance
export const matchWebSocket = new MatchWebSocket();

// ============ Fixtures API (Cloud Integration) ============

export interface CloudTournament {
  id: string;
  name: string;
  season: string;
  country?: string;
  fixture_count?: number;
}

export interface CloudFixture {
  id: string;
  tournament_id?: string;
  tournament?: {
    id: string;
    name: string;
    short_name?: string;
    season?: string;
    year?: string;
    sponsor?: string;
    hashtag?: string;
    tagline?: string;
  };
  home_team: {
    id: string;
    name: string;
    short_name?: string;
    logo_url?: string;
    primary_color?: string;
  };
  away_team: {
    id: string;
    name: string;
    short_name?: string;
    logo_url?: string;
    primary_color?: string;
  };
  venue?: string;
  scheduled_date?: string;
  matchday?: number;
  round?: string;
  status?: string;
}

export const fixturesApi = {
  // Get tournaments from cloud (via local backend proxy)
  async getCloudTournaments() {
    return apiGet<CloudTournament[]>('/fixtures/cloud/tournaments');
  },

  // Get fixtures for a tournament from cloud
  async getCloudTournamentFixtures(tournamentId: string) {
    return apiGet<{ tournament: CloudTournament; fixtures: CloudFixture[] }>(
      `/fixtures/cloud/tournaments/${tournamentId}`
    );
  },

  // Get all cloud fixtures
  async getCloudFixtures() {
    return apiGet<CloudFixture[]>('/fixtures/cloud/fixtures');
  },

  // Get single cloud fixture details
  async getCloudFixture(fixtureId: string) {
    return apiGet<CloudFixture>(`/fixtures/cloud/fixtures/${fixtureId}`);
  },

  // Load fixture from cloud into local database
  async loadCloudFixture(fixtureId: string) {
    return apiPost<{ success: boolean; message: string; fixture?: CloudFixture }>(
      '/fixtures/cloud/load',
      { fixture_id: fixtureId }
    );
  },

  // Get fixtures from local database
  async getLocalFixtures() {
    return apiGet<CloudFixture[]>('/fixtures');
  },

  // Send the final result of the latest match for a fixture to the fixtures server
  async uploadResult(fixtureId: string) {
    return apiPost<{ success: boolean; fixture_id: string }>(`/fixtures/upload/${encodeURIComponent(fixtureId)}`);
  },
};

// ============ Weather API ============

export interface WeatherData {
  venue: string;
  date: string;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  weather: {
    temperature: number;
    humidity: number;
    wind_speed: number;
    wind_direction: number;
    conditions: string;
    precipitation: number;
  };
}

export const weatherApi = {
  // Get weather for a venue
  async getWeatherForVenue(venueName: string, date?: string) {
    const dateParam = date ? `?date=${date}` : '';
    return apiGet<WeatherData>(`/weather/${encodeURIComponent(venueName)}${dateParam}`);
  },

  // Get weather by coordinates
  async getWeatherByCoords(latitude: number, longitude: number, date?: string) {
    const dateParam = date ? `&date=${date}` : '';
    return apiGet<WeatherData>(`/weather/coords?latitude=${latitude}&longitude=${longitude}${dateParam}`);
  },
};

// ============ Health Check ============

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${BASE_URL}/`);
    return response.ok;
  } catch {
    return false;
  }
}

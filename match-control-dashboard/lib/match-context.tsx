"use client"

/**
 * Match Context - Connected to Backend
 * 
 * This re-exports the backend-connected match context.
 * All match operations are now sent to the FastAPI backend.
 */

export { MatchProvider, useMatch } from "./match-context-backend"

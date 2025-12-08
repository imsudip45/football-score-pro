"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { 
  Cloud, 
  Sun, 
  CloudRain, 
  CloudSnow, 
  CloudFog, 
  Wind, 
  Droplets, 
  Thermometer,
  RefreshCw,
  MapPin,
  Loader2
} from "lucide-react"
import { weatherApi, type WeatherData } from "@/lib/api"
import { useMatch } from "@/lib/match-context"

function getWeatherIcon(conditions: string) {
  const cond = conditions.toLowerCase()
  if (cond.includes("rain") || cond.includes("shower") || cond.includes("drizzle")) {
    return <CloudRain className="h-8 w-8 text-blue-400" />
  }
  if (cond.includes("snow") || cond.includes("sleet")) {
    return <CloudSnow className="h-8 w-8 text-blue-200" />
  }
  if (cond.includes("fog") || cond.includes("mist")) {
    return <CloudFog className="h-8 w-8 text-gray-400" />
  }
  if (cond.includes("cloud") || cond.includes("overcast")) {
    return <Cloud className="h-8 w-8 text-gray-400" />
  }
  if (cond.includes("clear") || cond.includes("sunny")) {
    return <Sun className="h-8 w-8 text-yellow-400" />
  }
  return <Cloud className="h-8 w-8 text-gray-400" />
}

function getWindDirection(degrees: number): string {
  const directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
  const index = Math.round(degrees / 45) % 8
  return directions[index]
}

export function WeatherWidget() {
  const { match } = useMatch()
  const [weather, setWeather] = useState<WeatherData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const venue = match.venue

  const fetchWeather = async () => {
    if (!venue) {
      setError("No venue set for this match")
      return
    }

    setLoading(true)
    setError(null)
    
    try {
      const result = await weatherApi.getWeatherForVenue(venue)
      if (result.data) {
        setWeather(result.data)
      } else {
        setError(result.error || "Failed to fetch weather")
      }
    } catch (err) {
      setError("Failed to fetch weather data")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (venue) {
      fetchWeather()
    }
  }, [venue])

  if (!venue) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Cloud className="h-4 w-4" />
            Weather
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No venue set</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Cloud className="h-4 w-4" />
            Match Day Weather
          </CardTitle>
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-6 w-6" 
            onClick={fetchWeather}
            disabled={loading}
          >
            <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading && !weather ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="text-center py-4">
            <p className="text-sm text-muted-foreground">{error}</p>
            <Button variant="link" size="sm" onClick={fetchWeather} className="mt-2">
              Retry
            </Button>
          </div>
        ) : weather ? (
          <div className="space-y-4">
            {/* Venue */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <MapPin className="h-3 w-3" />
              {weather.venue}
            </div>

            {/* Main weather display */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {getWeatherIcon(weather.weather.conditions)}
                <div>
                  <div className="text-3xl font-bold">
                    {Math.round(weather.weather.temperature)}°C
                  </div>
                  <div className="text-sm text-muted-foreground capitalize">
                    {weather.weather.conditions}
                  </div>
                </div>
              </div>
            </div>

            {/* Weather details */}
            <div className="grid grid-cols-3 gap-4 pt-2 border-t">
              <div className="text-center">
                <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
                  <Droplets className="h-3 w-3" />
                </div>
                <div className="text-sm font-medium">{weather.weather.humidity}%</div>
                <div className="text-xs text-muted-foreground">Humidity</div>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
                  <Wind className="h-3 w-3" />
                </div>
                <div className="text-sm font-medium">
                  {Math.round(weather.weather.wind_speed)} km/h
                </div>
                <div className="text-xs text-muted-foreground">
                  Wind {getWindDirection(weather.weather.wind_direction)}
                </div>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
                  <CloudRain className="h-3 w-3" />
                </div>
                <div className="text-sm font-medium">{weather.weather.precipitation} mm</div>
                <div className="text-xs text-muted-foreground">Precip.</div>
              </div>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

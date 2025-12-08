"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { EventModal } from "./event-modal"
import type { EventType } from "@/lib/types"
import { Goal, AlertTriangle, Users, Target } from "lucide-react"

interface EventButton {
  type: EventType
  label: string
  icon: React.ReactNode
  variant: "default" | "destructive" | "outline" | "secondary"
}

const eventButtons: EventButton[] = [
  { type: "goal", label: "Goal", icon: <Goal className="h-5 w-5" />, variant: "default" },
  { type: "own_goal", label: "Own Goal", icon: <Goal className="h-5 w-5" />, variant: "destructive" },
  { type: "yellow_card", label: "Yellow Card", icon: <AlertTriangle className="h-5 w-5" />, variant: "secondary" },
  { type: "red_card", label: "Red Card", icon: <AlertTriangle className="h-5 w-5" />, variant: "destructive" },
  { type: "second_yellow", label: "2nd Yellow", icon: <AlertTriangle className="h-5 w-5" />, variant: "destructive" },
  { type: "substitution", label: "Substitution", icon: <Users className="h-5 w-5" />, variant: "outline" },
  { type: "penalty_scored", label: "Pen Scored", icon: <Target className="h-5 w-5" />, variant: "default" },
  { type: "penalty_missed", label: "Pen Missed", icon: <Target className="h-5 w-5" />, variant: "outline" },
]

export function QuickEvents() {
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedEventType, setSelectedEventType] = useState<EventType>("goal")

  const handleEventClick = (eventType: EventType) => {
    setSelectedEventType(eventType)
    setModalOpen(true)
  }

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Quick Events</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {eventButtons.map((button) => (
              <Button
                key={button.type}
                variant={button.variant}
                className="h-16 flex flex-col gap-1"
                onClick={() => handleEventClick(button.type)}
              >
                {button.icon}
                <span className="text-xs">{button.label}</span>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <EventModal open={modalOpen} onClose={() => setModalOpen(false)} eventType={selectedEventType} />
    </>
  )
}

"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Subject } from "@/types"

const TOPICS: Record<Subject, string[]> = {
  Physics: [
    "Current Electricity", "Electrostatics", "Magnetism & EMI",
    "Mechanics", "Modern Physics", "Optics",
    "Properties of Matter", "Semiconductors", "Thermodynamics", "Waves"
  ],
  Chemistry: [
    "Atomic Structure", "Chemical Equilibrium", "Chemical Kinetics",
    "Electrochemistry", "Environmental Chemistry", "Inorganic Chemistry",
    "Mole Concept", "Organic Chemistry", "Solutions",
    "Surface Chemistry", "Thermodynamics"
  ],
  Maths: [
    "Algebra", "Calculus", "Coordinate Geometry", "Mathematical Reasoning",
    "Probability", "Sets & Functions", "Trigonometry", "Vectors"
  ],
  Biology: [
    "Animal Kingdom", "Cell Biology", "Ecology", "Evolution",
    "Genetics", "Human Physiology", "Plant Kingdom",
    "Plant Physiology", "Reproduction"
  ],
}

const SUBJECTS: Subject[] = ["Physics", "Chemistry", "Maths", "Biology"]

interface Props {
  onStart: (subject: Subject, topic: string | null) => void
  isLoading: boolean
}

export function SubjectSelector({ onStart, isLoading }: Props) {
  const [selectedSubject, setSelectedSubject] = useState<Subject | null>(null)

  if (selectedSubject) {
    return (
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSelectedSubject(null)}
            className="text-slate-400 hover:text-white text-sm transition-colors"
          >
            ← Back
          </button>
          <h3 className="text-sm font-medium text-slate-300">
            {selectedSubject} — Select Topic
          </h3>
        </div>

        {/* Topic grid */}
        <div className="grid grid-cols-2 gap-2">
          {TOPICS[selectedSubject].map((topic) => (
            <Button
              key={topic}
              variant="outline"
              className="h-12 text-sm text-white border-slate-700 hover:border-blue-500 hover:bg-blue-500/10 text-left justify-start px-3"
              disabled={isLoading}
              onClick={() => onStart(selectedSubject, topic)}
            >
              {topic}
            </Button>
          ))}
        </div>

        {/* Skip topic — start with all topics */}
        <Button
          variant="ghost"
          className="w-full text-slate-400 hover:text-white border border-dashed border-slate-700 hover:border-slate-500"
          disabled={isLoading}
          onClick={() => onStart(selectedSubject, null)}
        >
          All Topics (no preference)
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-slate-300">Select Subject</h3>
      <div className="grid grid-cols-2 gap-3">
        {SUBJECTS.map((subject) => (
          <Button
            key={subject}
            variant="outline"
            className="h-16 text-base text-white border-slate-700 hover:border-blue-500 hover:bg-blue-500/10 bg-slate-800"
            disabled={isLoading}
            onClick={() => setSelectedSubject(subject)}
          >
            {subject}
          </Button>
        ))}
      </div>
    </div>
  )
}
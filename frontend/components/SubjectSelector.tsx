"use client"
// frontend/components/SubjectSelector.tsx

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Subject, DifficultyLevel, DifficultyMode } from "@/types"

// static data

const TOPICS: Record<Subject, string[]> = {
  Physics: [
    "Current Electricity", "Electrostatics", "Magnetism & EMI",
    "Mechanics", "Modern Physics", "Optics",
    "Properties of Matter", "Semiconductors", "Thermodynamics", "Waves",
  ],
  Chemistry: [
    "Atomic Structure", "Chemical Equilibrium", "Chemical Kinetics",
    "Electrochemistry", "Environmental Chemistry", "Inorganic Chemistry",
    "Mole Concept", "Organic Chemistry", "Solutions",
    "Surface Chemistry", "Thermodynamics",
  ],
  Maths: [
    "Algebra", "Calculus", "Coordinate Geometry", "Mathematical Reasoning",
    "Probability", "Sets & Functions", "Trigonometry", "Vectors",
  ],
  Biology: [
    "Animal Kingdom", "Cell Biology", "Ecology", "Evolution",
    "Genetics", "Human Physiology", "Plant Kingdom",
    "Plant Physiology", "Reproduction",
  ],
}

const SUBJECTS: Subject[] = ["Physics", "Chemistry", "Maths", "Biology"]

const DIFFICULTY_LEVELS: { value: DifficultyLevel; label: string; color: string; bg: string; border: string }[] = [
  {
    value: "Beginner",
    label: "Beginner",
    color: "text-green-400",
    bg: "bg-green-500/10 hover:bg-green-500/20",
    border: "border-green-500/40",
  },
  {
    value: "Intermediate",
    label: "Intermediate",
    color: "text-yellow-400",
    bg: "bg-yellow-500/10 hover:bg-yellow-500/20",
    border: "border-yellow-500/40",
  },
  {
    value: "Advanced",
    label: "Advanced",
    color: "text-red-400",
    bg: "bg-red-500/10 hover:bg-red-500/20",
    border: "border-red-500/40",
  },
]

// prop types

interface Props {
  onStart: (
    subject: Subject,
    topic: string | null,
    difficultyMode: DifficultyMode,
    fixedDifficulty: DifficultyLevel | null,
  ) => void
  isLoading: boolean
}

// component 

type Step = "subject" | "topic" | "difficulty"

export function SubjectSelector({ onStart, isLoading }: Props) {
  const [step, setStep] = useState<Step>("subject")
  const [selectedSubject, setSelectedSubject] = useState<Subject | null>(null)
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null)
  const [selectedDifficulty, setSelectedDifficulty] = useState<DifficultyLevel>("Beginner")
  const [difficultyMode, setDifficultyMode] = useState<DifficultyMode>("adaptive")

  // handlers

  function handleSubject(subject: Subject) {
    setSelectedSubject(subject)
    setStep("topic")
  }

  function handleTopic(topic: string | null) {
    setSelectedTopic(topic)
    setStep("difficulty")
  }

  function handleStart() {
    if (!selectedSubject) return
    onStart(
      selectedSubject,
      selectedTopic,
      difficultyMode,
      selectedDifficulty,
    )
  }

  function goBack() {
    if (step === "topic") setStep("subject")
    if (step === "difficulty") setStep("topic")
  }

  // breadcrumb

  const Breadcrumb = () => (
    <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-4">
      <button
        onClick={() => setStep("subject")}
        className={`hover:text-slate-300 transition-colors ${step === "subject" ? "text-slate-300 font-medium" : ""}`}
      >
        Subject
      </button>
      {step !== "subject" && (
        <>
          <span>/</span>
          <button
            onClick={() => setStep("topic")}
            className={`hover:text-slate-300 transition-colors ${step === "topic" ? "text-slate-300 font-medium" : ""}`}
          >
            {selectedSubject}
          </button>
        </>
      )}
      {step === "difficulty" && (
        <>
          <span>/</span>
          <span className="text-slate-300 font-medium">
            {selectedTopic ?? "All Topics"}
          </span>
          <span>/</span>
          <span className="text-blue-400 font-medium">Difficulty</span>
        </>
      )}
    </div>
  )

  // Step 1: Subject

  if (step === "subject") {
    return (
      <div className="space-y-3">
        <Breadcrumb />
        <h3 className="text-sm font-medium text-slate-300">Select Subject</h3>
        <div className="grid grid-cols-2 gap-3">
          {SUBJECTS.map((subject) => (
            <Button
              key={subject}
              variant="outline"
              className="h-16 text-base text-white border-slate-700 hover:border-blue-500 hover:bg-blue-500/10 bg-slateate-800"
              disabled={isLoading}
              onClick={() => handleSubject(subject)}
            >
              {subject}
            </Button>
          ))}
        </div>
      </div>
    )
  }

  // Step 2: Topic

  if (step === "topic") {
    return (
      <div className="space-y-4">
        <Breadcrumb />
        <div className="flex items-center gap-3">
          <button
            onClick={goBack}
            className="text-slate-400 hover:text-white text-sm transition-colors"
          >
            ← Back
          </button>
          <h3 className="text-sm font-medium text-slate-300">
            {selectedSubject} — Select Topic
          </h3>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {TOPICS[selectedSubject!].map((topic) => (
            <Button
              key={topic}
              variant="outline"
              className="h-12 text-sm text-white border-slate-700 hover:border-blue-500 hover:bg-blue-500/10 text-left justify-start px-3"
              disabled={isLoading}
              onClick={() => handleTopic(topic)}
            >
              {topic}
            </Button>
          ))}
        </div>

        <Button
          variant="ghost"
          className="w-full text-slate-400 hover:text-white border border-dashed border-slate-700 hover:border-slate-500"
          disabled={isLoading}
          onClick={() => handleTopic(null)}
        >
          All Topics (no preference)
        </Button>
      </div>
    )
  }

  // Step 3: Difficulty 

  return (
    <div className="space-y-5">
      <Breadcrumb />

      <div className="flex items-center gap-3">
        <button
          onClick={goBack}
          className="text-slate-400 hover:text-white text-sm transition-colors"
        >
          ← Back
        </button>
        <h3 className="text-sm font-medium text-slate-300">
          Choose Difficulty
        </h3>
      </div>

      {/* Difficulty level picker */}
      <div className="space-y-2">
        <p className="text-xs text-slate-500 uppercase tracking-wider">Starting Difficulty</p>
        <div className="grid grid-cols-3 gap-2">
          {DIFFICULTY_LEVELS.map((d) => (
            <button
              key={d.value}
              onClick={() => setSelectedDifficulty(d.value)}
              className={`
                rounded-lg border py-3 text-sm font-semibold transition-all
                ${d.bg} ${d.border} ${d.color}
                ${selectedDifficulty === d.value
                  ? "ring-2 ring-offset-1 ring-offset-background ring-current scale-[1.03] shadow-md"
                  : "opacity-70 hover:opacity-100"
                }
              `}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      {/* Mode toggle */}
      <div className="space-y-2">
        <p className="text-xs text-slate-500 uppercase tracking-wider">Progression Mode</p>
        <div className="grid grid-cols-2 gap-2">

          {/* Adaptive card */}
          <button
            onClick={() => setDifficultyMode("adaptive")}
            className={`
              relative rounded-xl border p-4 text-left transition-all
              ${difficultyMode === "adaptive"
                ? "border-blue-500 bg-blue-500/10 ring-1 ring-blue-500/40"
                : "border-slate-700 bg-slate-800/40 hover:border-slate-500"
              }
            `}
          >
            {difficultyMode === "adaptive" && (
              <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-blue-400" />
            )}
            <p className={`text-sm font-semibold mb-1 ${difficultyMode === "adaptive" ? "text-blue-400" : "text-slate-300"}`}>
              Adaptive
            </p>
            <p className="text-xs text-slate-500 leading-relaxed">
              Starts at {selectedDifficulty}, then escalates every 3 questions solved.
            </p>
            <p className="text-xs text-slate-600 mt-1.5 font-mono">
              Beginner → Intermediate → Advanced
            </p>
          </button>

          {/* Fixed card */}
          <button
            onClick={() => setDifficultyMode("fixed")}
            className={`
              relative rounded-xl border p-4 text-left transition-all
              ${difficultyMode === "fixed"
                ? "border-purple-500 bg-purple-500/10 ring-1 ring-purple-500/40"
                : "border-slate-700 bg-slate-800/40 hover:border-slate-500"
              }
            `}
          >
            {difficultyMode === "fixed" && (
              <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-purple-400" />
            )}
            <p className={`text-sm font-semibold mb-1 ${difficultyMode === "fixed" ? "text-purple-400" : "text-slate-300"}`}>
              Fixed
            </p>
            <p className="text-xs text-slate-500 leading-relaxed">
              Stay at <span className="font-medium text-slate-400">{selectedDifficulty}</span> for as long as you practice — no escalation.
            </p>
            <p className="text-xs text-slate-600 mt-1.5 font-mono">
              {selectedDifficulty} → {selectedDifficulty} → {selectedDifficulty}
            </p>
          </button>

        </div>
      </div>

      {/* Summary banner */}
      <div className="rounded-lg bg-slate-800/60 border border-slate-700 px-4 py-3 text-xs text-slate-400 space-y-0.5">
        <div className="flex justify-between">
          <span className="text-slate-500">Subject</span>
          <span className="text-white font-medium">{selectedSubject}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Topic</span>
          <span className="text-white font-medium">{selectedTopic ?? "All Topics"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Difficulty</span>
          <span className="font-medium text-white">{selectedDifficulty}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Mode</span>
          <span className={`font-medium ${difficultyMode === "adaptive" ? "text-blue-400" : "text-purple-400"}`}>
            {difficultyMode === "adaptive" ? "Adaptive (escalates)" : "Fixed (stays at level)"}
          </span>
        </div>
      </div>

      {/* Start button */}
      <Button
        className="w-full h-11 text-base font-semibold"
        disabled={isLoading}
        onClick={handleStart}
      >
        {isLoading ? "Starting session…" : "Start Session →"}
      </Button>
    </div>
  )
}
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

const SUBJECT_ICONS: Record<Subject, string> = {
  Physics: "⚡",
  Chemistry: "⚗️",
  Maths: "∑",
  Biology: "🧬",
}

const DIFFICULTY_LEVELS: {
  value: DifficultyLevel
  label: string
  color: string
  bg: string
  border: string
  selectedBorder: string
  selectedBg: string
}[] = [
  {
    value: "Beginner",
    label: "Beginner",
    color: "text-emerald-700",
    bg: "bg-emerald-50 hover:bg-emerald-100",
    border: "border-emerald-200",
    selectedBorder: "border-emerald-500",
    selectedBg: "bg-emerald-50",
  },
  {
    value: "Intermediate",
    label: "Intermediate",
    color: "text-amber-700",
    bg: "bg-amber-50 hover:bg-amber-100",
    border: "border-amber-200",
    selectedBorder: "border-amber-500",
    selectedBg: "bg-amber-50",
  },
  {
    value: "Advanced",
    label: "Advanced",
    color: "text-red-700",
    bg: "bg-red-50 hover:bg-red-100",
    border: "border-red-200",
    selectedBorder: "border-red-500",
    selectedBg: "bg-red-50",
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
    <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-4">
      <button
        onClick={() => setStep("subject")}
        className={`hover:text-gray-700 transition-colors ${step === "subject" ? "text-gray-700 font-medium" : ""}`}
      >
        Subject
      </button>
      {step !== "subject" && (
        <>
          <span className="text-gray-300">/</span>
          <button
            onClick={() => setStep("topic")}
            className={`hover:text-gray-700 transition-colors ${step === "topic" ? "text-gray-700 font-medium" : ""}`}
          >
            {selectedSubject}
          </button>
        </>
      )}
      {step === "difficulty" && (
        <>
          <span className="text-gray-300">/</span>
          <span className="text-gray-700 font-medium">
            {selectedTopic ?? "All Topics"}
          </span>
          <span className="text-gray-300">/</span>
          <span className="text-indigo-600 font-medium">Difficulty</span>
        </>
      )}
    </div>
  )

  // Step 1: Subject

  if (step === "subject") {
    return (
      <div className="space-y-3">
        <Breadcrumb />
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Select Subject</p>
        <div className="grid grid-cols-2 gap-2.5">
          {SUBJECTS.map((subject) => (
            <button
              key={subject}
              className="h-16 flex flex-col items-center justify-center gap-1 rounded-lg border border-gray-200 bg-white hover:border-indigo-400 hover:bg-indigo-50 text-gray-800 font-medium text-sm transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isLoading}
              onClick={() => handleSubject(subject)}
            >
              <span className="text-lg">{SUBJECT_ICONS[subject]}</span>
              <span className="text-xs font-semibold text-gray-700">{subject}</span>
            </button>
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
            className="text-gray-400 hover:text-gray-700 text-sm transition-colors"
          >
            ← Back
          </button>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            {selectedSubject} — Select Topic
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {TOPICS[selectedSubject!].map((topic) => (
            <Button
              key={topic}
              variant="outline"
              className="h-10 text-xs text-gray-700 border-gray-200 hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-700 text-left justify-start px-3 bg-white"
              disabled={isLoading}
              onClick={() => handleTopic(topic)}
            >
              {topic}
            </Button>
          ))}
        </div>

        <Button
          variant="ghost"
          className="w-full text-gray-400 hover:text-gray-700 border border-dashed border-gray-300 hover:border-gray-400 bg-transparent text-sm"
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
          className="text-gray-400 hover:text-gray-700 text-sm transition-colors"
        >
          ← Back
        </button>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
          Choose Difficulty
        </p>
      </div>

      {/* Difficulty level picker */}
      <div className="space-y-2">
        <p className="text-xs text-gray-400 uppercase tracking-wider">Starting Level</p>
        <div className="grid grid-cols-3 gap-2">
          {DIFFICULTY_LEVELS.map((d) => (
            <button
              key={d.value}
              onClick={() => setSelectedDifficulty(d.value)}
              className={`
                rounded-lg border py-2.5 text-xs font-semibold transition-all
                ${selectedDifficulty === d.value
                  ? `${d.selectedBg} ${d.selectedBorder} ${d.color} ring-2 ring-offset-1 ring-current scale-[1.02] shadow-sm`
                  : `${d.bg} ${d.border} ${d.color} opacity-70 hover:opacity-100`
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
        <p className="text-xs text-gray-400 uppercase tracking-wider">Progression Mode</p>
        <div className="grid grid-cols-2 gap-2">

          {/* Adaptive card */}
          <button
            onClick={() => setDifficultyMode("adaptive")}
            className={`
              relative rounded-xl border p-3.5 text-left transition-all
              ${difficultyMode === "adaptive"
                ? "border-indigo-400 bg-indigo-50 ring-1 ring-indigo-300"
                : "border-gray-200 bg-white hover:border-gray-300"
              }
            `}
          >
            {difficultyMode === "adaptive" && (
              <span className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-indigo-500" />
            )}
            <p className={`text-xs font-semibold mb-1 ${difficultyMode === "adaptive" ? "text-indigo-700" : "text-gray-700"}`}>
              Adaptive
            </p>
            <p className="text-[10px] text-gray-500 leading-relaxed">
              Starts at {selectedDifficulty}, escalates every 3 correct answers.
            </p>
            <p className={`text-[10px] mt-1.5 font-mono ${difficultyMode === "adaptive" ? "text-indigo-400" : "text-gray-300"}`}>
              B → I → A
            </p>
          </button>

          {/* Fixed card */}
          <button
            onClick={() => setDifficultyMode("fixed")}
            className={`
              relative rounded-xl border p-3.5 text-left transition-all
              ${difficultyMode === "fixed"
                ? "border-violet-400 bg-violet-50 ring-1 ring-violet-300"
                : "border-gray-200 bg-white hover:border-gray-300"
              }
            `}
          >
            {difficultyMode === "fixed" && (
              <span className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-violet-500" />
            )}
            <p className={`text-xs font-semibold mb-1 ${difficultyMode === "fixed" ? "text-violet-700" : "text-gray-700"}`}>
              Fixed
            </p>
            <p className="text-[10px] text-gray-500 leading-relaxed">
              Stays at <span className="font-medium text-gray-700">{selectedDifficulty}</span> — no escalation.
            </p>
            <p className={`text-[10px] mt-1.5 font-mono ${difficultyMode === "fixed" ? "text-violet-400" : "text-gray-300"}`}>
              {selectedDifficulty[0]} → {selectedDifficulty[0]} → {selectedDifficulty[0]}
            </p>
          </button>

        </div>
      </div>

      {/* Summary banner */}
      <div className="rounded-lg bg-gray-50 border border-gray-200 px-3.5 py-3 text-xs text-gray-500 space-y-1.5">
        {[
          ["Subject", selectedSubject],
          ["Topic", selectedTopic ?? "All Topics"],
          ["Difficulty", selectedDifficulty],
          ["Mode", difficultyMode === "adaptive" ? "Adaptive (escalates)" : "Fixed (stays at level)"],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between">
            <span className="text-gray-400">{label}</span>
            <span className={`font-medium ${label === "Mode" && difficultyMode === "adaptive" ? "text-indigo-600" : label === "Mode" ? "text-violet-600" : "text-gray-800"}`}>
              {value}
            </span>
          </div>
        ))}
      </div>

      {/* Start button */}
      <Button
        className="w-full h-10 text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white border-0"
        disabled={isLoading}
        onClick={handleStart}
      >
        {isLoading ? "Starting session…" : "Start Session →"}
      </Button>
    </div>
  )
}
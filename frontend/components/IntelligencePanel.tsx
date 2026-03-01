// frontend/components/IntelligencePanel.tsx

"use client"

import { useState } from "react"
import { Question, DifficultyLevel } from "@/types"

const DIFFICULTY_COLOR: Record<DifficultyLevel, string> = {
    Beginner: "text-green-400",
    Intermediate: "text-yellow-400",
    Advanced: "text-red-400",
}

const DIFFICULTY_BAR: Record<DifficultyLevel, number> = {
    Beginner: 25,
    Intermediate: 60,
    Advanced: 90,
}

interface Props {
    question: Question
    recommendedDifficulty: DifficultyLevel
    cosineDistance: number
}

export function IntelligencePanel({
    question,
    recommendedDifficulty,
    cosineDistance,
}: Props) {
    const [devMode, setDevMode] = useState(false)

    const similarityScore = Math.round((1 - cosineDistance) * 100)
    const difficultyScore = question.difficulty_score ?? 0
    const difficultyPct = Math.round(difficultyScore * 100)
    const barWidth = DIFFICULTY_BAR[recommendedDifficulty]

    return (
        <div className="w-full rounded-lg border border-slate-800 bg-slate-900/60 p-4 space-y-3">

            {/* Header row */}
            <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    AI Intelligence
                </span>
                <button
                    onClick={() => setDevMode((v) => !v)}
                    className={`text-xs px-2 py-0.5 rounded border transition-colors ${devMode
                            ? "border-blue-500 text-blue-400 bg-blue-500/10"
                            : "border-slate-700 text-slate-500 hover:border-slate-500"
                        }`}
                >
                    {devMode ? "Dev Mode ON" : "Dev Mode"}
                </button>
            </div>

            {/* Core metrics — always visible */}
            <div className="grid grid-cols-3 gap-3">

                {/* Difficulty Level */}
                <div className="flex flex-col gap-1">
                    <span className="text-xs text-slate-500">Difficulty</span>
                    <span className={`text-sm font-bold ${DIFFICULTY_COLOR[recommendedDifficulty]}`}>
                        {recommendedDifficulty}
                    </span>
                    <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className={`h-full rounded-full transition-all duration-500 ${recommendedDifficulty === "Beginner"
                                    ? "bg-green-400"
                                    : recommendedDifficulty === "Intermediate"
                                        ? "bg-yellow-400"
                                        : "bg-red-400"
                                }`}
                            style={{ width: `${barWidth}%` }}
                        />
                    </div>
                </div>

                {/* Semantic Similarity */}
                <div className="flex flex-col gap-1">
                    <span className="text-xs text-slate-500">Relevance</span>
                    <span className="text-sm font-bold text-blue-400">
                        {similarityScore}%
                    </span>
                    <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-blue-400 rounded-full transition-all duration-500"
                            style={{ width: `${similarityScore}%` }}
                        />
                    </div>
                </div>

                {/* Difficulty Score */}
                <div className="flex flex-col gap-1">
                    <span className="text-xs text-slate-500">Score</span>
                    <span className="text-sm font-bold text-purple-400">
                        {difficultyPct}%
                    </span>
                    <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-purple-400 rounded-full transition-all duration-500"
                            style={{ width: `${difficultyPct}%` }}
                        />
                    </div>
                </div>

            </div>

            {/* Dev Mode — raw values */}
            {devMode && (
                <div className="border-t border-slate-800 pt-3 grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="flex justify-between">
                        <span className="text-slate-500">question_id</span>
                        <span className="text-slate-300 truncate ml-2 max-w-[120px]">
                            {question.id.slice(0, 8)}...
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-slate-500">cosine_dist</span>
                        <span className="text-slate-300">{cosineDistance.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-slate-500">difficulty_score</span>
                        <span className="text-slate-300">{difficultyScore.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-slate-500">formula_present</span>
                        <span className={question.formula_present ? "text-green-400" : "text-slate-500"}>
                            {question.formula_present ? "yes" : "no"}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-slate-500">keyword_density</span>
                        <span className="text-slate-300">
                            {question.keyword_density?.toFixed(3) ?? "n/a"}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-slate-500">est_time</span>
                        <span className="text-slate-300">
                            {question.estimated_time ? `${question.estimated_time}s` : "n/a"}
                        </span>
                    </div>
                </div>
            )}

        </div>
    )
}
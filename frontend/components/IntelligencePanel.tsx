// frontend/components/IntelligencePanel.tsx

"use client"

import { useState } from "react"
import { Question, DifficultyLevel } from "@/types"

const DIFFICULTY_COLOR: Record<DifficultyLevel, string> = {
    Beginner: "text-emerald-600",
    Intermediate: "text-amber-600",
    Advanced: "text-red-600",
}

const DIFFICULTY_BAR: Record<DifficultyLevel, { width: number; color: string }> = {
    Beginner: { width: 25, color: "bg-emerald-400" },
    Intermediate: { width: 60, color: "bg-amber-400" },
    Advanced: { width: 90, color: "bg-red-400" },
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
    const { width: barWidth, color: difficulty_color } = DIFFICULTY_BAR[recommendedDifficulty]

    return (
        <div className="w-full rounded-lg border border-gray-200 bg-white p-4 space-y-4 shadow-sm">

            {/* Header row */}
            <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    AI Intelligence
                </span>
                <button
                    onClick={() => setDevMode((v) => !v)}
                    className={`text-xs px-2 py-0.5 rounded border transition-colors ${devMode
                        ? "border-indigo-400 text-indigo-600 bg-indigo-50"
                        : "border-gray-200 text-gray-400 hover:border-gray-400"
                        }`}
                >
                    {devMode ? "Dev Mode ON" : "Dev Mode"}
                </button>
            </div>

            {/* Core metrics — always visible */}
            <div className="grid grid-cols-3 gap-4">

                {/* Difficulty Level */}
                <div className="flex flex-col gap-1.5">
                    <span className="text-xs text-gray-400">Difficulty</span>
                    <span className={`text-sm font-bold ${DIFFICULTY_COLOR[recommendedDifficulty]}`}>
                        {recommendedDifficulty}
                    </span>
                    <div className="h-1 w-full bg-gray-100 rounded-full overflow-hidden">
                        <div
                            className={`h-full rounded-full transition-all duration-500 ${difficulty_color}`}
                            style={{ width: `${barWidth}%` }}
                        />
                    </div>
                </div>

                {/* Semantic Similarity */}
                <div className="flex flex-col gap-1.5">
                    <span className="text-xs text-gray-400">Relevance</span>
                    <span className="text-sm font-bold text-indigo-600">
                        {similarityScore}%
                    </span>
                    <div className="h-1 w-full bg-gray-100 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-indigo-400 rounded-full transition-all duration-500"
                            style={{ width: `${similarityScore}%` }}
                        />
                    </div>
                </div>

                {/* Difficulty Score */}
                <div className="flex flex-col gap-1.5">
                    <span className="text-xs text-gray-400">Score</span>
                    <span className="text-sm font-bold text-violet-600">
                        {difficultyPct}%
                    </span>
                    <div className="h-1 w-full bg-gray-100 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-violet-400 rounded-full transition-all duration-500"
                            style={{ width: `${difficultyPct}%` }}
                        />
                    </div>
                </div>

            </div>

            {/* Dev Mode — raw values */}
            {devMode && (
                <div className="border-t border-gray-100 pt-3 grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="flex justify-between">
                        <span className="text-gray-400">question_id</span>
                        <span className="text-gray-700 truncate ml-2 max-w-[120px]">
                            {question.id.slice(0, 8)}...
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-400">cosine_dist</span>
                        <span className="text-gray-700">{cosineDistance.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-400">difficulty_score</span>
                        <span className="text-gray-700">{difficultyScore.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-400">formula_present</span>
                        <span className={question.formula_present ? "text-emerald-600" : "text-gray-400"}>
                            {question.formula_present ? "yes" : "no"}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-400">keyword_density</span>
                        <span className="text-gray-700">
                            {question.keyword_density?.toFixed(3) ?? "n/a"}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-400">est_time</span>
                        <span className="text-gray-700">
                            {question.estimated_time ? `${question.estimated_time}s` : "n/a"}
                        </span>
                    </div>
                </div>
            )}

        </div>
    )
}
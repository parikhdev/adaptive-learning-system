"use client"

import { useSessionStore } from "@/lib/store/session"

export function SessionStats() {
    const { totalQuestions, skippedQuestions, subject, currentDifficulty } =
        useSessionStore()

    const stats = [
        { value: totalQuestions, label: "Answered", color: "text-gray-900" },
        { value: skippedQuestions, label: "Skipped", color: "text-amber-600" },
        { value: subject, label: "Subject", color: "text-indigo-600" },
        { value: currentDifficulty, label: "Level", color: "text-gray-900" },
    ]

    return (
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm px-6 py-4">
            <div className="flex items-center justify-center gap-10">
                {stats.map((stat) => (
                    <div key={stat.label} className="flex flex-col items-center gap-0.5">
                        <span className={`text-2xl font-bold tabular-nums ${stat.color}`}>
                            {stat.value}
                        </span>
                        <span className="text-xs text-gray-400 font-medium">{stat.label}</span>
                    </div>
                ))}
            </div>
        </div>
    )
}
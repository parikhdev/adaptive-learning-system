"use client"

import { useSessionStore } from "@/lib/store/session"

export function SessionStats() {
    const { totalQuestions, skippedQuestions, subject, currentDifficulty } =
        useSessionStore()

    return (
        <div className="flex items-center justify-center gap-8 w-full py-2">
            <div className="flex flex-col items-center">
                <span className="text-3xl font-bold text-white">{totalQuestions}</span>
                <span className="text-slate-400 text-xs mt-1">Answered</span>
            </div>
            <div className="flex flex-col items-center">
                <span className="text-3xl font-bold text-yellow-400">{skippedQuestions}</span>
                <span className="text-slate-400 text-xs mt-1">Skipped</span>
            </div>
            <div className="flex flex-col items-center">
                <span className="text-3xl font-bold text-primary">{subject}</span>
                <span className="text-slate-400 text-xs mt-1">Subject</span>
            </div>
            <div className="flex flex-col items-center">
                <span className="text-3xl font-bold text-white">{currentDifficulty}</span>
                <span className="text-slate-400 text-xs mt-1">Level</span>
            </div>
        </div>
    )
}
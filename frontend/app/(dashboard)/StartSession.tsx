"use client"
// frontend/app/(dashboard)/StartSession.tsx

import { useState } from "react"
import { useRouter } from "next/navigation"
import { SubjectSelector } from "@/components/SubjectSelector"
import { startSession } from "@/lib/api/explain"
import { useSessionStore } from "@/lib/store/session"
import { Subject, DifficultyLevel, DifficultyMode } from "@/types"

export function StartSession({ studentId }: { studentId: string }) {
    const router = useRouter()
    const { setSession, resetSession } = useSessionStore()
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    async function handleStart(
        subject: Subject,
        topic: string | null,
        difficultyMode: DifficultyMode,
        fixedDifficulty: DifficultyLevel | null,
    ) {
        setIsLoading(true)
        setError(null)
        try {
            const session = await startSession(
                studentId,
                subject,
                difficultyMode,
                fixedDifficulty,
            )
            resetSession()
            setSession(
                session.id,
                studentId,
                subject,
                topic,
                difficultyMode,
                fixedDifficulty,
            )
            router.push(`/session/${session.id}`)
        } catch {
            setError("Failed to start session. Is the backend running?")
            setIsLoading(false)
        }
    }

    return (
        <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-900">Start a Session</h2>
            {error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</p>}
            <SubjectSelector onStart={handleStart} isLoading={isLoading} />
        </div>
    )
}
"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { SubjectSelector } from "@/components/SubjectSelector"
import { startSession } from "@/lib/api/explain"
import { useSessionStore } from "@/lib/store/session"
import { Subject } from "@/types"

export function StartSession({ studentId }: { studentId: string }) {
    const router = useRouter()
    const { setSession, resetSession } = useSessionStore()
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    async function handleStart(subject: Subject, topic: string | null) {
        setIsLoading(true)
        setError(null)

        try {
            const session = await startSession(studentId, subject)
            resetSession()                               // clear previous session state
            setSession(session.id, studentId, subject, topic)
            router.push(`/session/${session.id}`)
        } catch {
            setError("Failed to start session. Is the backend running?")
            setIsLoading(false)
        }
    }

    return (
        <div className="space-y-4">
            <h2 className="text-xl font-semibold text-white">Start a Session</h2>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <SubjectSelector onStart={handleStart} isLoading={isLoading} />
        </div>
    )
}
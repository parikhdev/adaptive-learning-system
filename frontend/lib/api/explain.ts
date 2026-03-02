// frontend/lib/api/explain.ts

import { ExplainRequest, ExplainResponse } from "@/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL

export async function fetchExplanation(
    payload: ExplainRequest
): Promise<ExplainResponse> {
    const res = await fetch(`${API_URL}/explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    })

    if (!res.ok) {
        const error = await res.json().catch(() => ({}))
        throw new Error(error.detail ?? `Explain failed: ${res.status}`)
    }

    return res.json()
}

export async function startSession(
    student_id: string,
    subject: string
): Promise<{ id: string }> {
    const res = await fetch(`${API_URL}/sessions/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id, subject }),
    })

    if (!res.ok) {
        throw new Error(`Session start failed: ${res.status}`)
    }

    return res.json()
}

export async function recordAnswer(
    session_id: string,
    question_id: string,
    is_correct: boolean,
    time_taken: number,
    skipped?: boolean
): Promise<void> {
    const res = await fetch(`${API_URL}/sessions/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id, question_id, is_correct, time_taken, skipped: skipped ?? false }),
    })

    if (!res.ok) {
        console.error("Failed to record answer:", await res.text())
    }
}
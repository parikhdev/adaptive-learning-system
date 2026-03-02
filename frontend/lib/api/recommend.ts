// frontend/lib/api/recommend.ts

import { RecommendRequest, RecommendResponse } from "@/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL

export async function fetchRecommendation(
    payload: RecommendRequest
): Promise<RecommendResponse> {
    const res = await fetch(`${API_URL}/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    })

    if (!res.ok) {
        const error = await res.json().catch(() => ({}))
        throw new Error(error.detail ?? `Recommend failed: ${res.status}`)
    }

    return res.json()
}
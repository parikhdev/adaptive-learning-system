"use client"
// frontend/app/(dashboard)/session/[id]/page.tsx

import { useEffect, useState, useCallback, useRef } from "react"
import { useParams } from "next/navigation"
import { useSessionStore } from "@/lib/store/session"
import { fetchRecommendation } from "@/lib/api/recommend"
import { fetchExplanation, recordAnswer } from "@/lib/api/explain"
import { QuestionCard } from "@/components/QuestionCard"
import { ExplanationPanel } from "@/components/ExplanationPanel"
import { SessionStats } from "@/components/SessionStats"
import { IntelligencePanel } from "@/components/IntelligencePanel"
import { ExplainResponse, DifficultyLevel } from "@/types"

export default function SessionPage() {
    const { id: sessionId } = useParams<{ id: string }>()

    const {
        studentId,
        subject,
        topic,
        difficultyMode,
        fixedDifficulty,
        currentQuestion,
        currentDifficulty,
        selectedAnswer,
        showExplanation,
        isLoading,
        setQuestion,
        submitAnswer,
        skipQuestion,
        setLoading,
        nextQuestion,
    } = useSessionStore()

    const [explanation, setExplanation] = useState<ExplainResponse | null>(null)
    const [explanationLoading, setExplanationLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [recommendedDifficulty, setRecommendedDifficulty] = useState<DifficultyLevel>("Intermediate")

    const answerStartTime = useRef<number>(Date.now())

    // Keep a ref to the latest store values so loadNextQuestion always reads
    // fresh values even when called from inside a stale closure (e.g. after
    // Zustand hydration from sessionStorage finishes after the first render).
    const storeRef = useRef({ difficultyMode, fixedDifficulty, studentId, subject, topic })
    useEffect(() => {
        storeRef.current = { difficultyMode, fixedDifficulty, studentId, subject, topic }
    })

    const loadNextQuestion = useCallback(async () => {
        // Read directly from ref so we always get the latest Zustand values,
        // not the values captured when this callback was first created.
        const { studentId, subject, topic, difficultyMode, fixedDifficulty } = storeRef.current
        if (!studentId || !subject) return

        setLoading(true)
        setError(null)
        try {
            const result = await fetchRecommendation({
                session_id: sessionId,
                student_id: studentId,
                subject,
                topic: topic ?? undefined,
                difficulty_mode: difficultyMode,
                // Always send fixed_difficulty — in adaptive mode it tells the backend
                // which level to START from. In fixed mode it is the permanent level.
                fixed_difficulty: fixedDifficulty ?? undefined,
            })
            setQuestion(result.question, result.recommended_difficulty)
            setRecommendedDifficulty(result.recommended_difficulty)
            answerStartTime.current = Date.now()
        } catch {
            setError("Failed to load question. Please try again.")
        } finally {
            setLoading(false)
        }
    }, [sessionId, setQuestion, setLoading])  // sessionId is stable; store read via ref

    // Load first question once store has hydrated (100ms lets sessionStorage restore)
    useEffect(() => {
        const timer = setTimeout(() => {
            if (storeRef.current.studentId && storeRef.current.subject) {
                loadNextQuestion()
            }
        }, 100)
        return () => clearTimeout(timer)
    }, [loadNextQuestion])

    async function handleAnswer(answer: string) {
        if (!currentQuestion || selectedAnswer) return
        const timeTaken = Math.round((Date.now() - answerStartTime.current) / 1000)

        await recordAnswer(sessionId, currentQuestion.id, false, timeTaken)
        submitAnswer(answer, false)

        setExplanationLoading(true)
        try {
            const result = await fetchExplanation({
                session_id: sessionId,
                question_id: currentQuestion.id,
                student_answer: answer,
                subject: currentQuestion.subject,
                topic: currentQuestion.topic ?? undefined,
                difficulty_level: currentQuestion.difficulty_level,
            })
            setExplanation(result)
        } catch {
            setExplanation(null)
        } finally {
            setExplanationLoading(false)
        }
    }

    async function handleSkip() {
        if (!currentQuestion) return
        const timeTaken = Math.round((Date.now() - answerStartTime.current) / 1000)
        await recordAnswer(sessionId, currentQuestion.id, false, timeTaken, true)
        skipQuestion()
        await loadNextQuestion()
    }

    async function handleNext() {
        nextQuestion()
        setExplanation(null)
        await loadNextQuestion()
    }

    if (!storeRef.current.studentId || !storeRef.current.subject) {
        return (
            <div className="text-center py-20">
                <p className="text-slate-400">Session not found.</p>
                <a href="/" className="text-primary hover:underline text-sm">
                    Return to dashboard
                </a>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <SessionStats />

            {error && !currentQuestion && (
                <p className="text-sm text-red-400">{error}</p>
            )}

            {isLoading && !currentQuestion && (
                <div className="flex items-center justify-center py-20">
                    <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                </div>
            )}

            {currentQuestion && (
                <>
                    <QuestionCard
                        question={currentQuestion}
                        difficulty={currentDifficulty}
                        onAnswer={handleAnswer}
                        disabled={!!selectedAnswer}
                        selectedAnswer={selectedAnswer}
                    />
                    <IntelligencePanel
                        question={currentQuestion}
                        recommendedDifficulty={recommendedDifficulty}
                        cosineDistance={currentQuestion.cosine_distance}
                    />
                    {!selectedAnswer && (
                        <div className="flex justify-end">
                            <button
                                onClick={handleSkip}
                                className="text-sm text-slate-500 hover:text-slate-300 transition-colors underline underline-offset-2"
                            >
                                Skip this question →
                            </button>
                        </div>
                    )}
                </>
            )}

            {showExplanation && (
                <ExplanationPanel
                    explanation={explanation}
                    isLoading={explanationLoading}
                    onNext={handleNext}
                />
            )}
        </div>
    )
}
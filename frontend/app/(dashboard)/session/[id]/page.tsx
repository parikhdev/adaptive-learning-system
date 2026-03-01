"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { useParams } from "next/navigation"
import { useSessionStore } from "@/lib/store/session"
import { fetchRecommendation } from "@/lib/api/recommend"
import { fetchExplanation, recordAnswer } from "@/lib/api/explain"
import { QuestionCard } from "@/components/QuestionCard"
import { ExplanationPanel } from "@/components/ExplanationPanel"
import { SessionStats } from "@/components/SessionStats"
import { ExplainResponse, DifficultyLevel } from "@/types"
import { IntelligencePanel } from "@/components/IntelligencePanel"


export default function SessionPage() {
    const { id: sessionId } = useParams<{ id: string }>()

    const {
        studentId,
        subject,
        topic,
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
    const answerStartTime = useRef<number>(Date.now())
    const [recommendedDifficulty, setRecommendedDifficulty] = useState<DifficultyLevel>("Intermediate")

    const loadNextQuestion = useCallback(async () => {
        if (!studentId || !subject) return
        setLoading(true)
        setError(null)
        try {
            const result = await fetchRecommendation({
                session_id: sessionId,
                student_id: studentId,
                subject,
                topic: topic ?? undefined,
            })
            setQuestion(result.question, result.recommended_difficulty)
            setRecommendedDifficulty(result.recommended_difficulty)
            answerStartTime.current = Date.now()   // reset timer for new question
        } catch {
            setError("Failed to load question. Please try again.")
        } finally {
            setLoading(false)
        }
    }, [sessionId, studentId, subject, topic, setQuestion, setLoading])

    useEffect(() => {
        const timer = setTimeout(() => {
            if (studentId && subject) {
                loadNextQuestion()
            }
        }, 100)

        return () => clearTimeout(timer)
    }, [studentId, subject])

    async function handleAnswer(answer: string) {
        if (!currentQuestion || selectedAnswer) return

        const timeTaken = Math.round((Date.now() - answerStartTime.current) / 1000)

        // Record answer in backend 
        await recordAnswer(
            sessionId,
            currentQuestion.id,
            false,
            timeTaken,
        )

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

    if (!studentId || !subject) {
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

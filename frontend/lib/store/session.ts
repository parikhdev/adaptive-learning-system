"use client"

import { create } from "zustand"
import { persist, createJSONStorage } from "zustand/middleware"
import { Question, DifficultyLevel } from "@/types"

interface SessionState {
    sessionId: string | null
    studentId: string | null
    subject: string | null
    topic: string | null
    currentQuestion: Question | null
    currentDifficulty: DifficultyLevel
    totalQuestions: number
    correctAnswers: number
    skippedQuestions: number
    isLoading: boolean
    showExplanation: boolean
    lastAnswerCorrect: boolean | null
    selectedAnswer: string | null

    setSession: (sessionId: string, studentId: string, subject: string, topic: string | null) => void
    setQuestion: (question: Question, difficulty: DifficultyLevel) => void
    submitAnswer: (answer: string, isCorrect: boolean) => void
    skipQuestion: () => void
    setLoading: (loading: boolean) => void
    setShowExplanation: (show: boolean) => void
    nextQuestion: () => void
    resetSession: () => void
}

export const useSessionStore = create<SessionState>()(
    persist(
        (set) => ({
            sessionId: null,
            studentId: null,
            subject: null,
            topic: null,
            currentQuestion: null,
            currentDifficulty: "Intermediate",
            totalQuestions: 0,
            correctAnswers: 0,
            skippedQuestions: 0,
            isLoading: false,
            showExplanation: false,
            lastAnswerCorrect: null,
            selectedAnswer: null,

            setSession: (sessionId, studentId, subject, topic) =>
                set({ sessionId, studentId, subject, topic }),

            setQuestion: (question, difficulty) =>
                set({
                    currentQuestion: question,
                    currentDifficulty: difficulty,
                    selectedAnswer: null,
                    showExplanation: false,
                    lastAnswerCorrect: null,
                }),

            submitAnswer: (answer, _isCorrect) =>
                set((state) => ({
                    selectedAnswer: answer,
                    lastAnswerCorrect: null,
                    totalQuestions: state.totalQuestions + 1,
                    correctAnswers: state.correctAnswers,
                    showExplanation: true,
                })),

            skipQuestion: () =>
                set((state) => ({
                    skippedQuestions: state.skippedQuestions + 1,
                    selectedAnswer: null,
                    showExplanation: false,
                    lastAnswerCorrect: null,
                    currentQuestion: null,
                })),

            setLoading: (loading) => set({ isLoading: loading }),

            setShowExplanation: (show) => set({ showExplanation: show }),

            nextQuestion: () =>
                set({
                    selectedAnswer: null,
                    showExplanation: false,
                    lastAnswerCorrect: null,
                    currentQuestion: null,
                }),

            resetSession: () =>
                set({
                    sessionId: null,
                    studentId: null,
                    subject: null,
                    topic: null,
                    currentQuestion: null,
                    currentDifficulty: "Intermediate",
                    totalQuestions: 0,
                    correctAnswers: 0,
                    skippedQuestions: 0,
                    isLoading: false,
                    showExplanation: false,
                    lastAnswerCorrect: null,
                    selectedAnswer: null,
                }),
        }),
        {
            name: "als-session-storage",
            storage: createJSONStorage(() => sessionStorage),
            partialize: (state) => ({
                sessionId: state.sessionId,
                studentId: state.studentId,
                subject: state.subject,
                topic: state.topic,
                currentDifficulty: state.currentDifficulty,
                totalQuestions: state.totalQuestions,
                correctAnswers: state.correctAnswers,
                skippedQuestions: state.skippedQuestions,
            }),
        }
    )
)
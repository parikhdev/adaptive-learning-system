"use client"
// frontend/lib/store/session.ts

import { create } from "zustand"
import { persist, createJSONStorage } from "zustand/middleware"
import { Question, DifficultyLevel, DifficultyMode } from "@/types"

interface SessionState {
    // session identity 
    sessionId: string | null
    studentId: string | null
    subject: string | null
    topic: string | null

    // difficulty config (NEW)
    difficultyMode: DifficultyMode    // "adaptive" | "fixed"
    fixedDifficulty: DifficultyLevel | null  // only meaningful in fixed mode

    // current question state
    currentQuestion: Question | null
    currentDifficulty: DifficultyLevel
    selectedAnswer: string | null
    showExplanation: boolean
    lastAnswerCorrect: boolean | null

    // session stats 
    totalQuestions: number
    correctAnswers: number
    skippedQuestions: number

    // ui state 
    isLoading: boolean

    // actions 
    setSession: (
        sessionId: string,
        studentId: string,
        subject: string,
        topic: string | null,
        difficultyMode: DifficultyMode,
        fixedDifficulty: DifficultyLevel | null,
    ) => void
    setQuestion: (question: Question, difficulty: DifficultyLevel) => void
    submitAnswer: (answer: string, isCorrect: boolean) => void
    skipQuestion: () => void
    setLoading: (loading: boolean) => void
    setShowExplanation: (show: boolean) => void
    nextQuestion: () => void
    resetSession: () => void
}

const DEFAULT_STATE = {
    sessionId: null,
    studentId: null,
    subject: null,
    topic: null,
    difficultyMode: "adaptive" as DifficultyMode,
    fixedDifficulty: null,
    currentQuestion: null,
    currentDifficulty: "Intermediate" as DifficultyLevel,
    selectedAnswer: null,
    showExplanation: false,
    lastAnswerCorrect: null,
    totalQuestions: 0,
    correctAnswers: 0,
    skippedQuestions: 0,
    isLoading: false,
}

export const useSessionStore = create<SessionState>()(
    persist(
        (set) => ({
            ...DEFAULT_STATE,

            setSession: (sessionId, studentId, subject, topic, difficultyMode, fixedDifficulty) =>
                set({ sessionId, studentId, subject, topic, difficultyMode, fixedDifficulty }),

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

            resetSession: () => set(DEFAULT_STATE),
        }),
        {
            name: "als-session-storage",
            storage: createJSONStorage(() => sessionStorage),
            partialize: (state) => ({
                sessionId: state.sessionId,
                studentId: state.studentId,
                subject: state.subject,
                topic: state.topic,
                difficultyMode: state.difficultyMode,
                fixedDifficulty: state.fixedDifficulty,
                currentDifficulty: state.currentDifficulty,
                totalQuestions: state.totalQuestions,
                correctAnswers: state.correctAnswers,
                skippedQuestions: state.skippedQuestions,
            }),
        },
    ),
)
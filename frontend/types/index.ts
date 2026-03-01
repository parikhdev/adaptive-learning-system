// frontend/types/index.ts

export type DifficultyLevel = "Beginner" | "Intermediate" | "Advanced"

export type Subject = "Physics" | "Chemistry" | "Maths" | "Biology"

export interface Question {
    id: string
    original_text: string
    subject: string
    topic: string | null
    subtopic: string | null
    difficulty_level: DifficultyLevel
    difficulty_score: number | null
    estimated_time: number | null
    formula_present: boolean | null
    keyword_density: number | null
    cosine_distance: number
}

export interface RecommendRequest {
    session_id: string
    student_id: string
    subject: string
    topic?: string
}

export interface RecommendResponse {
    session_id: string
    student_id: string
    recommended_difficulty: DifficultyLevel
    question: Question
    debug?: Record<string, unknown>
}

export interface ExplainRequest {
    session_id: string
    question_id: string
    student_answer: string
    subject: string
    topic?: string
    difficulty_level?: DifficultyLevel
}

export interface ExplainResponse {
    question_id: string
    subject: string
    topic: string | null
    student_answer: string
    explanation: string
    similar_questions_used: number
    latency_ms: number
}

export interface SessionStartRequest {
    student_id: string
    subject: string
}

export interface SessionStartResponse {
    id: string
    student_id: string
    subject: string
    started_at: string
}

export interface AnswerRequest {
    session_id: string
    question_id: string
    student_answer: string
    is_correct: boolean
    time_taken: number
}

export interface StudentStats {
    student_id: string
    total_sessions: number
    total_questions: number
    correct_answers: number
    accuracy: number
}
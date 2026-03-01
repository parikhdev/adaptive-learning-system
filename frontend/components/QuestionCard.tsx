"use client"

import { useEffect, useRef } from "react"
import katex from "katex"
import "katex/dist/katex.min.css"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { DifficultyBadge } from "./DifficultyBadge"
import { Question, DifficultyLevel } from "@/types"

// Render text with inline LaTeX using KaTeX
function MathText({ text }: { text: string }) {
    const ref = useRef<HTMLSpanElement>(null)

    useEffect(() => {
        if (!ref.current) return

        // Split on LaTeX delimiters: \(...\) \[...\] $...$ $$...$$
        const parts = text.split(
            /(\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$|\$[^$]*?\$)/
        )

        ref.current.innerHTML = parts
            .map((part) => {
                const inlineMatch = part.match(/^\\\(([\s\S]*?)\\\)$/) ||
                    part.match(/^\$((?:[^$])*?)\$$/)
                const blockMatch = part.match(/^\\\[([\s\S]*?)\\\]$/) ||
                    part.match(/^\$\$([\s\S]*?)\$\$$/)

                if (inlineMatch) {
                    try {
                        return katex.renderToString(inlineMatch[1], {
                            throwOnError: false,
                            displayMode: false,
                        })
                    } catch { return part }
                }

                if (blockMatch) {
                    try {
                        return katex.renderToString(blockMatch[1], {
                            throwOnError: false,
                            displayMode: true,
                        })
                    } catch { return part }
                }

                // Plain text — escape HTML
                return part
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
            })
            .join("")
    }, [text])

    return <span ref={ref} />
}

const OPTION_LABELS = ["A", "B", "C", "D"]

function parseOptions(text: string): {
    questionText: string
    options: Record<string, string>
} {
    const options: Record<string, string> = {}

    // Pass 1: newline-based parsing
    const lines = text.split("\n").map((l) => l.trim()).filter(Boolean)
    const questionLines: string[] = []
    let parsingOptions = false

    for (const line of lines) {
        const strictMatch = line.match(/^([A-Da-d])\s*[.)]\s*(.+)/)
        if (strictMatch) {
            const key = strictMatch[1].toUpperCase()
            const value = strictMatch[2].trim()
            if (value && value.toLowerCase() !== "nan" && value.length > 1) {
                options[key] = value
                parsingOptions = true
            }
        } else if (!parsingOptions) {
            questionLines.push(line)
        }
    }

    if (Object.keys(options).length >= 2) {
        return { questionText: questionLines.join(" "), options }
    }

    // Pass 2: inline parsing — no lookbehind, manual split
    // Find first A. or A) that starts an options block
    const inlinePattern = /\s([A-D])\s*[.)]\s*/g
    const matches: { index: number; key: string }[] = []
    let m: RegExpExecArray | null

    while ((m = inlinePattern.exec(text)) !== null) {
        matches.push({ index: m.index, key: m[1] })
    }

    if (matches.length >= 2) {
        const firstOptionIndex = matches[0].index
        const questionText = text.slice(0, firstOptionIndex).trim()
        const freshOptions: Record<string, string> = {}

        for (let i = 0; i < matches.length; i++) {
            const start = matches[i].index
            const end = i + 1 < matches.length ? matches[i + 1].index : text.length
            const chunk = text.slice(start, end).trim()
            const cm = chunk.match(/^[^A-Da-d]*([A-Da-d])\s*[.)]\s*([\s\S]+)/)
            if (cm) {
                const key = cm[1].toUpperCase()
                const value = cm[2].trim().replace(/\s+/g, " ")
                if (value && value.toLowerCase() !== "nan" && value.length > 1) {
                    freshOptions[key] = value
                }
            }
        }

        if (Object.keys(freshOptions).length >= 2) {
            return { questionText, options: freshOptions }
        }
    }

    return { questionText: questionLines.join(" "), options }
  }

interface Props {
    question: Question
    difficulty: DifficultyLevel
    onAnswer: (answer: string) => void
    disabled: boolean
    selectedAnswer: string | null
}

export function QuestionCard({
    question,
    difficulty,
    onAnswer,
    disabled,
    selectedAnswer,
}: Props) {
    const { questionText, options } = parseOptions(question.original_text)
    const validOptions = OPTION_LABELS.filter((opt) => options[opt])
    const hasOptions = validOptions.length >= 2

    return (
        <Card className="w-full">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div className="flex items-center gap-2 flex-wrap">
                    {question.topic && question.topic.toLowerCase() !== "general" && (
                        <span className="text-sm text-slate-400">{question.topic}</span>
                    )}
                    {question.subtopic && question.subtopic.toLowerCase() !== "general" && (
                        <span className="text-sm text-slate-400">
                            {question.topic && question.topic.toLowerCase() !== "general" && "→ "}
                            {question.subtopic}
                        </span>
                    )}
                </div>
                <DifficultyBadge level={difficulty} />
            </CardHeader>

            <CardContent className="space-y-5">
                <p className="text-base leading-relaxed text-white">
                    <MathText text={questionText} />
                </p>

                {hasOptions ? (
                    <div className="grid grid-cols-1 gap-3">
                        {validOptions.map((opt) => (
                            <Button
                                key={opt}
                                variant="outline"
                                className={`justify-start h-auto py-3 px-4 text-left whitespace-normal text-white transition-colors ${selectedAnswer === opt
                                        ? "border-blue-500 bg-blue-500/20 hover:bg-blue-500/20"
                                        : "border-slate-700 hover:border-slate-500 hover:bg-slate-800"
                                    }`}
                                disabled={disabled}
                                onClick={() => onAnswer(opt)}
                            >
                                <span className="font-bold mr-3 shrink-0">{opt}.</span>
                                <MathText text={options[opt]} />
                            </Button>
                        ))}
                    </div>
                ) : (
                    <div className="space-y-3 border border-slate-700 rounded-md p-4">
                        <p className="text-sm text-slate-400 italic">
                            This question requires a written answer.
                        </p>
                        <Button
                            variant="outline"
                            className="w-full border-slate-600 text-slate-300 hover:border-blue-500 hover:text-white"
                            disabled={disabled}
                            onClick={() => onAnswer("A")}
                        >
                            Skip to next question →
                        </Button>
                    </div>
                )}

                {question.estimated_time && (
                    <p className="text-xs text-slate-500">
                        Estimated time: {Math.round(question.estimated_time / 60)} min
                    </p>
                )}
            </CardContent>
        </Card>
    )
}
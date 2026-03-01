"use client"

import { useEffect, useRef } from "react"
import katex from "katex"
import "katex/dist/katex.min.css"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ExplainResponse } from "@/types"

function MathText({ text }: { text: string }) {
    const ref = useRef<HTMLSpanElement>(null)

    useEffect(() => {
        if (!ref.current) return

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

                return part
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
            })
            .join("")
    }, [text])

    return <span ref={ref} />
}

interface Props {
    explanation: ExplainResponse | null
    isLoading: boolean
    onNext: () => void
}

export function ExplanationPanel({ explanation, isLoading, onNext }: Props) {
    if (isLoading) {
        return (
            <Card className="w-full border-blue-500/30 bg-blue-500/5">
                <CardContent className="pt-6">
                    <div className="flex items-center gap-3">
                        <div className="h-4 w-4 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
                        <p className="text-sm text-slate-400">Loading concept explanation...</p>
                    </div>
                </CardContent>
            </Card>
        )
    }

    if (!explanation) return null

    // Split explanation into paragraphs
    const paragraphs = explanation.explanation
        .split("\n")
        .map((p) => p.trim())
        .filter(Boolean)

    return (
        <Card className="w-full border-blue-500/30 bg-blue-500/5">
            <CardHeader className="pb-3">
                <CardTitle className="text-base text-blue-400 flex items-center gap-2">
                    <span>📘</span>
                    <span>Concept Reinforcement</span>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-3">
                    {paragraphs.map((para, i) => (
                        <p key={i} className="text-sm leading-relaxed text-slate-200">
                            <MathText text={para} />
                        </p>
                    ))}
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-blue-500/20">
                    <p className="text-xs text-slate-500">
                        Based on {explanation.similar_questions_used} similar questions
                    </p>
                    <Button onClick={onNext} size="sm">
                        Next Question →
                    </Button>
                </div>
            </CardContent>
        </Card>
    )
}
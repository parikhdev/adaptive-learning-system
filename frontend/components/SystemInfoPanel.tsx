// frontend/components/SystemInfoPanel.tsx
// Shows system-level information in the right column of the dashboard home page.
// No user data required — displays capabilities and session structure.

"use client"

import { useState } from "react"

const PIPELINE_STEPS = [
  {
    number: "01",
    title: "Semantic Embedding",
    description:
      "Subject & topic selection is encoded into a 384-dim vector using BAAI/bge-small-en-v1.5, a sentence-transformer fine-tuned on academic text.",
    icon: "⊕",
    color: "text-indigo-600",
    bg: "bg-indigo-50",
    border: "border-indigo-200",
  },
  {
    number: "02",
    title: "pgvector Retrieval",
    description:
      "A pgvector HNSW index over 121,557 JEE/NEET questions in Supabase is searched using cosine similarity (<=>) to surface the most relevant candidates.",
    icon: "⊗",
    color: "text-violet-600",
    bg: "bg-violet-50",
    border: "border-violet-200",
  },
  {
    number: "03",
    title: "Difficulty Filtering",
    description:
      "Candidates are filtered by difficulty level (Beginner / Intermediate / Advanced), assigned via a rule-based weighted composite score across 5 signals.",
    icon: "◈",
    color: "text-amber-600",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  {
    number: "04",
    title: "AI Explanation",
    description:
      "After each answer, similar questions are retrieved via RAG and injected into an LLM prompt to generate a personalised concept reinforcement.",
    icon: "◉",
    color: "text-emerald-600",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
  },
]

const DIFFICULTY_LEVELS = [
  {
    label: "Beginner",
    range: "Q1–3",
    score: "0.0–0.35",
    color: "text-emerald-700",
    bg: "bg-emerald-100",
    bar: "bg-emerald-400",
    pct: 25,
  },
  {
    label: "Intermediate",
    range: "Q4–6",
    score: "0.35–0.70",
    color: "text-amber-700",
    bg: "bg-amber-100",
    bar: "bg-amber-400",
    pct: 60,
  },
  {
    label: "Advanced",
    range: "Q7+",
    score: "0.70–1.0",
    color: "text-red-700",
    bg: "bg-red-100",
    bar: "bg-red-400",
    pct: 95,
  },
]

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4">
      <h3 className="text-sm font-semibold text-gray-900 tracking-tight">{title}</h3>
      {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
    </div>
  )
}

export function SystemInfoPanel() {
  const [activeTab, setActiveTab] = useState<"pipeline" | "difficulty" | "about">("pipeline")

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Tab header */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
        {(["pipeline", "difficulty", "about"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 text-xs font-medium py-1.5 px-2 rounded-md transition-all capitalize ${
              activeTab === tab
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab === "pipeline" ? "How It Works" : tab === "difficulty" ? "Difficulty" : "About"}
          </button>
        ))}
      </div>

      {/* Pipeline tab */}
      {activeTab === "pipeline" && (
        <div className="space-y-3">
          <SectionHeader
            title="Question Recommendation Pipeline"
            subtitle="Each question is selected in real-time via 4 stages"
          />
          <div className="space-y-2">
            {PIPELINE_STEPS.map((step, i) => (
              <div
                key={step.number}
                className={`relative flex gap-3 rounded-lg border p-3 ${step.bg} ${step.border}`}
              >
                <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold ${step.color} bg-white border ${step.border}`}>
                  {step.number}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-xs font-semibold ${step.color}`}>{step.title}</p>
                  <p className="text-xs text-gray-600 mt-0.5 leading-relaxed">{step.description}</p>
                </div>
                {i < PIPELINE_STEPS.length - 1 && (
                  <div className="absolute -bottom-2.5 left-[22px] w-px h-3 bg-gray-300 z-10" />
                )}
              </div>
            ))}
          </div>
          <div className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2.5 text-xs text-gray-500">
            <span className="font-medium text-gray-700">Dataset:</span> 121,557 JEE/NEET questions across Physics, Chemistry, Maths &amp; Biology, embedded with{" "}
            <span className="font-medium text-indigo-700">BAAI/bge-small-en-v1.5</span>
          </div>
        </div>
      )}

      {/* Difficulty tab */}
      {activeTab === "difficulty" && (
        <div className="space-y-4">
          <SectionHeader
            title="Adaptive Difficulty Progression"
            subtitle="In Adaptive mode, the system escalates difficulty automatically"
          />

          {/* Progression diagram */}
          <div className="relative">
            <div className="flex items-center gap-0">
              {DIFFICULTY_LEVELS.map((d, i) => (
                <div key={d.label} className="flex items-center flex-1">
                  <div className={`flex-1 rounded-lg border p-3 text-center ${d.bg} border-transparent`}>
                    <div className={`text-xs font-bold ${d.color}`}>{d.label}</div>
                    <div className="text-[10px] text-gray-500 mt-0.5">{d.range}</div>
                    <div className={`mt-2 h-1.5 w-full rounded-full bg-gray-200 overflow-hidden`}>
                      <div
                        className={`h-full rounded-full ${d.bar}`}
                        style={{ width: `${d.pct}%` }}
                      />
                    </div>
                    <div className="text-[10px] text-gray-400 mt-1">score {d.score}</div>
                  </div>
                  {i < DIFFICULTY_LEVELS.length - 1 && (
                    <div className="flex-shrink-0 px-1 text-gray-400 text-sm font-light">→</div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 divide-y divide-gray-100 text-xs">
            <div className="px-3 py-2.5 flex justify-between">
              <span className="text-gray-500">Escalation trigger</span>
              <span className="font-medium text-gray-800">3 questions answered at current level</span>
            </div>
            <div className="px-3 py-2.5 flex justify-between">
              <span className="text-gray-500">Demotion trigger</span>
              <span className="font-medium text-gray-800">None (level only increases)</span>
            </div>
            <div className="px-3 py-2.5 flex justify-between">
              <span className="text-gray-500">Fixed mode</span>
              <span className="font-medium text-gray-800">Difficulty stays constant</span>
            </div>
            <div className="px-3 py-2.5 flex justify-between">
              <span className="text-gray-500">Difficulty score method</span>
              <span className="font-medium text-indigo-700">Rule-based weighted composite</span>
            </div>
          </div>

          <div className="rounded-lg bg-indigo-50 border border-indigo-100 px-3 py-2.5 text-xs text-indigo-700">
            <span className="font-semibold">Scoring signals:</span> Length (25%), Formula density (25%), Symbol count (20%), Question type (20%), Keyword density (10%) — per-subject percentile tertile binning assigns Beginner / Intermediate / Advanced.
          </div>
        </div>
      )}

      {/* About tab */}
      {activeTab === "about" && (
        <div className="space-y-3">
          <SectionHeader
            title="System Overview"
            subtitle="Key design decisions and technical stack"
          />
          <div className="space-y-2">
            {[
              {
                label: "Retrieval Method",
                value: "pgvector (HNSW, cosine)",
                note: "Supabase / PostgreSQL vector index",
                color: "bg-indigo-50 border-indigo-100",
              },
              {
                label: "Embedding Model",
                value: "BAAI/bge-small-en-v1.5",
                note: "384-dim sentence-transformer",
                color: "bg-violet-50 border-violet-100",
              },
              {
                label: "Difficulty Scoring",
                value: "Rule-based composite",
                note: "5 signals, per-subject percentile binning",
                color: "bg-amber-50 border-amber-100",
              },
              {
                label: "Explanation Engine",
                value: "RAG + LLM",
                note: "Retrieved context injected into prompt",
                color: "bg-emerald-50 border-emerald-100",
              },
              {
                label: "Backend",
                value: "FastAPI + PostgreSQL",
                note: "REST API with Supabase auth",
                color: "bg-sky-50 border-sky-100",
              },
              {
                label: "Coverage",
                value: "4 subjects · 38 topics",
                note: "121,557 questions total",
                color: "bg-rose-50 border-rose-100",
              },
            ].map((item) => (
              <div
                key={item.label}
                className={`rounded-lg border px-3 py-2.5 ${item.color}`}
              >
                <div className="flex justify-between items-baseline gap-2">
                  <span className="text-xs text-gray-500">{item.label}</span>
                  <span className="text-xs font-semibold text-gray-900 text-right">{item.value}</span>
                </div>
                <p className="text-[10px] text-gray-400 mt-0.5">{item.note}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

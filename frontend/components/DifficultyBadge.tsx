// frontend/components/DifficultyBadge.tsx

import { Badge } from "@/components/ui/badge"
import { DifficultyLevel } from "@/types"

const config: Record<DifficultyLevel, { label: string; className: string }> = {
    Beginner: {
        label: "Beginner",
        className: "bg-emerald-100 text-emerald-700 border-emerald-200",
    },
    Intermediate: {
        label: "Intermediate",
        className: "bg-amber-100 text-amber-700 border-amber-200",
    },
    Advanced: {
        label: "Advanced",
        className: "bg-red-100 text-red-700 border-red-200",
    },
}

export function DifficultyBadge({ level }: { level: DifficultyLevel }) {
    const { label, className } = config[level]
    return (
        <Badge variant="outline" className={`text-xs font-medium ${className}`}>
            {label}
        </Badge>
    )
}
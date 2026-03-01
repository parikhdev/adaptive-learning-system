// frontend/components/DifficultyBadge.tsx

import { Badge } from "@/components/ui/badge"
import { DifficultyLevel } from "@/types"

const config: Record<DifficultyLevel, { label: string; className: string }> = {
    Beginner: {
        label: "Beginner",
        className: "bg-green-500/20 text-green-400 border-green-500/30",
    },
    Intermediate: {
        label: "Intermediate",
        className: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    },
    Advanced: {
        label: "Advanced",
        className: "bg-red-500/20 text-red-400 border-red-500/30",
    },
}

export function DifficultyBadge({ level }: { level: DifficultyLevel }) {
    const { label, className } = config[level]
    return (
        <Badge variant="outline" className={className}>
            {label}
        </Badge>
    )
}
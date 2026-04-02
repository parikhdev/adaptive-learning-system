import { createClient } from "@/lib/supabase/server"
import { redirect } from "next/navigation"
import { StartSession } from "./StartSession"
import { SystemInfoPanel } from "@/components/SystemInfoPanel"

export default async function DashboardPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect("/login")
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Welcome back</h1>
        <p className="text-sm text-gray-500 mt-1">
          {user.email} — ready to practice?
        </p>
      </div>

      {/* Two-column layout: session setup + system info */}
      <div className="grid grid-cols-1 lg:grid-cols-[440px_1fr] gap-6 items-start">
        {/* Left: session setup card */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <StartSession studentId={user.id} />
        </div>

        {/* Right: system info panel */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <SystemInfoPanel />
        </div>
      </div>
    </div>
  )
}
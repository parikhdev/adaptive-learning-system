import { createClient } from "@/lib/supabase/server"
import { StartSession } from "./StartSession"

export default async function DashboardPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white">Welcome back</h1>
        <p className="text-slate-400 mt-1">
          {user?.email} — ready to practice?
        </p>
      </div>
      <StartSession studentId={user!.id} />
    </div>
  )
}

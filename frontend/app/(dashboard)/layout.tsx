import { redirect } from "next/navigation"
import { createClient } from "@/lib/supabase/server"

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect("/login")
  }

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <span className="font-bold text-lg text-white">Adaptive Learning System</span>
        <form action="/auth/signout" method="post">
          <button
            type="submit"
            className="text-sm text-slate-400 hover:text-white transition-colors"
          >
            Sign out
          </button>
        </form>
      </nav>
      <main className="max-w-2xl mx-auto px-4 py-8">
        {children}
      </main>
    </div>
  )
}

// frontend/app/(auth)/login/page.tsx

"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { createClient } from "@/lib/supabase/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function LoginPage() {
    const router = useRouter()
    const supabase = createClient()

    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [error, setError] = useState<string | null>(null)
    const [loading, setLoading] = useState(false)

    async function handleLogin(e: React.FormEvent) {
        e.preventDefault()
        setLoading(true)
        setError(null)

        const { error } = await supabase.auth.signInWithPassword({ email, password })

        if (error) {
            setError(error.message)
            setLoading(false)
            return
        }

        router.push("/")
        router.refresh()
    }

    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
            {/* Logo / brand mark */}
            <div className="flex items-center gap-2.5 mb-8">
                <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-sm">
                    <span className="text-white text-sm font-bold">A</span>
                </div>
                <span className="text-gray-800 font-semibold text-base">Adaptive Learning System</span>
            </div>

            <Card className="w-full max-w-sm bg-white border-gray-200 shadow-sm">
                <CardHeader className="space-y-1 pb-4">
                    <CardTitle className="text-xl font-bold text-gray-900">Sign in</CardTitle>
                    <CardDescription className="text-gray-500 text-sm">
                        Continue your JEE/NEET preparation
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleLogin} className="space-y-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="email" className="text-xs font-medium text-gray-700">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="you@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                className="border-gray-200 text-gray-900 placeholder:text-gray-400 focus:border-indigo-400 focus:ring-indigo-200 text-sm"
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="password" className="text-xs font-medium text-gray-700">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                className="border-gray-200 text-gray-900 focus:border-indigo-400 focus:ring-indigo-200 text-sm"
                            />
                        </div>
                        {error && (
                            <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</p>
                        )}
                        <Button
                            type="submit"
                            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white border-0 text-sm font-semibold"
                            disabled={loading}
                        >
                            {loading ? "Signing in…" : "Sign In"}
                        </Button>
                        <p className="text-xs text-center text-gray-400">
                            No account?{" "}
                            <a href="/signup" className="text-indigo-600 hover:underline font-medium">
                                Sign up
                            </a>
                        </p>
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}
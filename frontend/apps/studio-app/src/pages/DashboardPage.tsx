import { useAuth0 } from '@auth0/auth0-react'
import { Spinner } from '@flowform/ui'

export function DashboardPage() {
  const { user, isAuthenticated, isLoading } = useAuth0()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-56px)] bg-background">
        <Spinner size={28} />
      </div>
    )
  }

  return (
    <main className="max-w-4xl mx-auto px-6 py-12">
      <h1>Dashboard</h1>
      {isAuthenticated && user ? (
        <p className="text-muted-foreground mt-2">Welcome back, {user.name ?? user.email}</p>
      ) : (
        <p className="text-muted-foreground mt-2">Sign in to manage your surveys and projects.</p>
      )}
    </main>
  )
}

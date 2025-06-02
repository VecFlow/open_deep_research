import { Sidebar } from '@/components/dashboard/sidebar'
import { Header } from '@/components/dashboard/header'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <div className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0">
        <Sidebar />
      </div>
      
      {/* Main content */}
      <div className="lg:pl-64 flex flex-col flex-1">
        <Header />
        <main className="flex-1 pb-8">
          {children}
        </main>
      </div>
    </div>
  )
}
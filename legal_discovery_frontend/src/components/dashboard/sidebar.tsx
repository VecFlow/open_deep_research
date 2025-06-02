'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { FileText, BarChart3, Settings, Home } from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/cases', icon: Home },
  { name: 'Cases', href: '/cases', icon: FileText },
  { name: 'Analytics', href: '/analytics', icon: BarChart3, disabled: true },
  { name: 'Settings', href: '/settings', icon: Settings, disabled: true },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="flex h-full flex-col bg-gray-900">
      {/* Logo */}
      <div className="flex h-16 items-center justify-center">
        <div className="flex items-center space-x-2">
          <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <FileText className="h-5 w-5 text-white" />
          </div>
          <span className="text-xl font-bold text-white">Legal AI</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navigation.map((item) => {
          const isActive = pathname.startsWith(item.href)
          const Icon = item.icon
          
          if (item.disabled) {
            return (
              <div
                key={item.name}
                className={cn(
                  'group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors opacity-50 cursor-not-allowed',
                  'text-gray-300'
                )}
              >
                <Icon className="mr-3 h-5 w-5 flex-shrink-0 text-gray-400" />
                {item.name}
              </div>
            )
          }
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors',
                isActive
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              )}
            >
              <Icon
                className={cn(
                  'mr-3 h-5 w-5 flex-shrink-0',
                  isActive ? 'text-white' : 'text-gray-400 group-hover:text-white'
                )}
              />
              {item.name}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-gray-700">
        <p className="text-xs text-gray-400">
          Legal Discovery v1.0.0
        </p>
      </div>
    </div>
  )
}
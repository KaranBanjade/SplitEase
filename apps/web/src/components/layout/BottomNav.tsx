import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Home, Users, Plus, ArrowLeftRight, User } from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItem {
  to: string
  icon: React.ReactNode
  label: string
  isFab?: boolean
}

const navItems: NavItem[] = [
  { to: '/', icon: <Home size={22} />, label: 'Home' },
  { to: '/groups', icon: <Users size={22} />, label: 'Groups' },
  { to: '/add', icon: <Plus size={24} />, label: 'Add', isFab: true },
  { to: '/activity', icon: <ArrowLeftRight size={22} />, label: 'Activity' },
  { to: '/profile', icon: <User size={22} />, label: 'Profile' },
]

export function BottomNav() {
  const navigate = useNavigate()
  const location = useLocation()

  const handleFabPress = () => {
    // Navigate to first group's add expense or groups page if no group
    const match = location.pathname.match(/\/groups\/([^/]+)/)
    if (match) {
      navigate(`/groups/${match[1]}/add-expense`)
    } else {
      navigate('/groups')
    }
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 pb-safe">
      <div className="bg-slate-900/95 backdrop-blur-md border-t border-slate-800 px-2 pt-2 pb-1">
        <nav className="flex items-center justify-around max-w-lg mx-auto">
          {navItems.map((item, index) => {
            if (item.isFab) {
              return (
                <motion.button
                  key="fab"
                  whileTap={{ scale: 0.9 }}
                  whileHover={{ scale: 1.05 }}
                  onClick={handleFabPress}
                  className="flex flex-col items-center relative -mt-6"
                >
                  <div className="w-14 h-14 rounded-full bg-primary-600 flex items-center justify-center shadow-xl shadow-primary-900/50 border-4 border-slate-900">
                    {item.icon}
                  </div>
                  <span className="text-[10px] mt-1 text-primary-400 font-medium">
                    {item.label}
                  </span>
                </motion.button>
              )
            }

            return (
              <NavLink
                key={item.to + index}
                to={item.to}
                end={item.to === '/'}
                className="flex flex-col items-center gap-0.5 py-1 px-3 group"
              >
                {({ isActive: navIsActive }) => {
                  const active = navIsActive
                  return (
                    <>
                      <div
                        className={cn(
                          'p-1.5 rounded-xl transition-colors',
                          active
                            ? 'text-primary-400 bg-primary-500/10'
                            : 'text-slate-500 group-hover:text-slate-300'
                        )}
                      >
                        {item.icon}
                      </div>
                      <span
                        className={cn(
                          'text-[10px] font-medium transition-colors',
                          active ? 'text-primary-400' : 'text-slate-500'
                        )}
                      >
                        {item.label}
                      </span>
                      {active && (
                        <motion.div
                          layoutId="nav-indicator"
                          className="absolute -bottom-1 w-1 h-1 rounded-full bg-primary-400"
                        />
                      )}
                    </>
                  )
                }}
              </NavLink>
            )
          })}
        </nav>
      </div>
    </div>
  )
}

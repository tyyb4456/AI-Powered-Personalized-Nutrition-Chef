// src/components/layout/Navbar.jsx

import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../store/AuthContext';
import { useTheme } from '../../store/ThemeContext';
import {
  LogOut, Leaf, User, BookOpen, Sparkles,
  CalendarDays, ClipboardList, Camera, BarChart2, Sun, Moon,
} from 'lucide-react';

const NAV_ITEMS = [
  { to: '/recipes',          icon: BookOpen,      label: 'Recipes'   },
  { to: '/recipes/generate', icon: Sparkles,      label: 'Generate'  },
  { to: '/meal-plan',        icon: CalendarDays,  label: 'Plan'      },
  { to: '/meal-log',         icon: ClipboardList, label: 'Log'       },
  { to: '/food-camera',      icon: Camera,        label: 'Camera'    },
  { to: '/analytics',        icon: BarChart2,     label: 'Analytics' },
  { to: '/profile',          icon: User,          label: 'Profile'   },
];

const NavLink = ({ to, icon: Icon, label, dark }) => {
  const { pathname } = useLocation();
  const active = pathname === to || pathname.startsWith(to + '/');
  return (
    <Link
      to={to}
      className={`relative flex items-center gap-1.5 text-xs font-medium tracking-wide px-3 py-2 rounded-lg transition-all duration-200 group ${
        active
          ? dark
            ? 'text-white bg-white/10'
            : 'text-gray-900 bg-black/8'
          : dark
            ? 'text-gray-400 hover:text-white hover:bg-white/8'
            : 'text-gray-500 hover:text-gray-900 hover:bg-black/5'
      }`}
    >
      <Icon size={13} />
      <span>{label}</span>
      {active && (
        <span className={`absolute bottom-0 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full ${dark ? 'bg-white' : 'bg-gray-900'}`} />
      )}
    </Link>
  );
};

const Navbar = () => {
  const { user, logout } = useAuth();
  const { dark, toggle } = useTheme();
  const navigate = useNavigate();

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 border-b backdrop-blur-xl transition-colors duration-300 ${
      dark
        ? 'bg-black/70 border-white/8'
        : 'bg-white/80 border-black/8'
    }`}>
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">

        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group shrink-0">
          <div className={`p-1.5 rounded-lg transition-colors ${dark ? 'bg-white/10 group-hover:bg-white/15' : 'bg-black/5 group-hover:bg-black/10'}`}>
            <Leaf size={15} className={dark ? 'text-white' : 'text-gray-900'} />
          </div>
          <span className={`text-sm font-semibold tracking-tight ${dark ? 'text-white' : 'text-gray-900'}`}>
            nutrition<span className={dark ? 'text-gray-500' : 'text-gray-400'}>.ai</span>
          </span>
        </Link>

        {/* Nav links */}
        {user && (
          <div className="hidden md:flex items-center gap-0.5">
            {NAV_ITEMS.map(item => (
              <NavLink key={item.to} {...item} dark={dark} />
            ))}
          </div>
        )}

        {/* Right side */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Theme toggle */}
          <button
            onClick={toggle}
            className={`p-2 rounded-lg transition-all duration-200 ${
              dark ? 'text-gray-400 hover:text-white hover:bg-white/8' : 'text-gray-500 hover:text-gray-900 hover:bg-black/5'
            }`}
          >
            {dark ? <Sun size={14} /> : <Moon size={14} />}
          </button>

          {user && (
            <>
              <span className={`text-xs hidden lg:block ${dark ? 'text-gray-500' : 'text-gray-400'}`}>
                {user.name}
              </span>
              <button
                onClick={() => { logout(); navigate('/login'); }}
                className={`flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg transition-all duration-200 ${
                  dark
                    ? 'text-gray-500 hover:text-red-400 hover:bg-red-400/8'
                    : 'text-gray-400 hover:text-red-500 hover:bg-red-50'
                }`}
              >
                <LogOut size={13} />
                <span className="hidden sm:block">Logout</span>
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
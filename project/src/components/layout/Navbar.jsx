// src/components/layout/Navbar.jsx

import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../store/AuthContext';
import { LogOut, Leaf, User, BookOpen, Sparkles, CalendarDays, ClipboardList } from 'lucide-react';

const NavLink = ({ to, icon: Icon, label }) => {
  const { pathname } = useLocation();
  const active = pathname === to || pathname.startsWith(to + '/');
  return (
    <Link
      to={to}
      className={`flex items-center gap-1.5 text-sm font-medium transition-colors px-3 py-1.5 rounded-lg ${
        active
          ? 'text-primary-700 bg-primary-50'
          : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
      }`}
    >
      <Icon size={15} />
      {label}
    </Link>
  );
};

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <Link to="/" className="flex items-center gap-2 text-primary-600 font-bold text-lg">
          <Leaf size={22} />
          <span>Nutrition AI</span>
        </Link>

        {user && (
          <div className="hidden sm:flex items-center gap-1">
            <NavLink to="/recipes"          icon={BookOpen}      label="Recipes"   />
            <NavLink to="/recipes/generate" icon={Sparkles}      label="Generate"  />
            <NavLink to="/meal-plan"        icon={CalendarDays}  label="Meal Plan" />
            <NavLink to="/meal-log"         icon={ClipboardList} label="Meal Log"  />
            <NavLink to="/profile"          icon={User}          label="Profile"   />
          </div>
        )}
      </div>

      {user && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500 hidden sm:block">{user.name}</span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1 text-sm text-gray-400 hover:text-red-600 transition-colors"
          >
            <LogOut size={15} />
            <span className="hidden sm:block">Logout</span>
          </button>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
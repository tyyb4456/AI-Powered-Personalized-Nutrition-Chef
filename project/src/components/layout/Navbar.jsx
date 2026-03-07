// src/components/layout/Navbar.jsx

import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../store/AuthContext';
import { LogOut, Leaf, User } from 'lucide-react';

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
      <Link to="/" className="flex items-center gap-2 text-primary-600 font-bold text-xl">
        <Leaf size={24} />
        <span>Nutrition AI</span>
      </Link>

      {user && (
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">
            Hello, <span className="font-semibold text-gray-900">{user.name}</span>
          </span>
          <Link
            to="/profile"
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-primary-600 transition-colors"
          >
            <User size={16} />
            Profile
          </Link>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-red-600 transition-colors"
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
// src/pages/DashboardPage.jsx

import { useAuth } from '../store/AuthContext';
import { Leaf } from 'lucide-react';

const DashboardPage = () => {
  const { user } = useAuth();

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-2">
          <Leaf className="text-primary-600" size={28} />
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        </div>
        <p className="text-gray-500 mb-8">Welcome back, {user?.name}! More features coming soon.</p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {['Recipes', 'Meal Plans', 'Analytics'].map((item) => (
            <div key={item} className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="text-sm font-medium text-gray-500 mb-1">{item}</div>
              <div className="text-2xl font-bold text-gray-900">—</div>
              <div className="text-xs text-gray-400 mt-1">Coming in next phases</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
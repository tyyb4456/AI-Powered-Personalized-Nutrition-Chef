// src/App.jsx

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './store/AuthContext';
import ProtectedRoute from './components/layout/ProtectedRoute';
import Navbar from './components/layout/Navbar';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import ProfilePage from './pages/ProfilePage';
import GenerateRecipePage from './pages/GenerateRecipePage';
import RecipesPage from './pages/RecipesPage';
import MealPlanPage from './pages/MealPlanPage';
import MealLogPage from './pages/MealLogPage';

const queryClient = new QueryClient();

const Layout = ({ children }) => (
  <div className="min-h-screen bg-gray-50">
    <Navbar />
    <main>{children}</main>
  </div>
);

const Wrap = ({ children }) => (
  <ProtectedRoute>
    <Layout>{children}</Layout>
  </ProtectedRoute>
);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
          <Routes>
            <Route path="/login"    element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            <Route path="/"                  element={<Wrap><DashboardPage /></Wrap>} />
            <Route path="/profile"           element={<Wrap><ProfilePage /></Wrap>} />
            <Route path="/recipes"           element={<Wrap><RecipesPage /></Wrap>} />
            <Route path="/recipes/generate"  element={<Wrap><GenerateRecipePage /></Wrap>} />
            <Route path="/meal-plan"         element={<Wrap><MealPlanPage /></Wrap>} />
            <Route path="/meal-log"          element={<Wrap><MealLogPage /></Wrap>} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
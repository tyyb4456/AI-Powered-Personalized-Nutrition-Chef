// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './store/AuthContext';
import { ThemeProvider, useTheme } from './store/ThemeContext';
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
import FoodCameraPage from './pages/FoodCameraPage';
import AnalyticsPage from './pages/AnalyticsPage';

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 1000 * 60 * 2, retry: 1 } },
});

const Layout = ({ children }) => {
  const { dark } = useTheme();
  return (
    <div className={`min-h-screen transition-colors duration-300 ${dark ? 'bg-[#080808]' : 'bg-[#f7f6f3]'}`}>
      <Navbar />
      <main className="pt-14.25">{children}</main>
    </div>
  );
};

const Wrap = ({ children }) => (
  <ProtectedRoute>
    <Layout>{children}</Layout>
  </ProtectedRoute>
);

const AppRoutes = () => {
  const { dark } = useTheme();
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: dark ? '#1a1a1a' : '#fff',
            color: dark ? '#fff' : '#111',
            border: dark ? '1px solid rgba(255,255,255,0.08)' : '1px solid rgba(0,0,0,0.08)',
            borderRadius: '12px',
            fontSize: '13px',
          },
        }}
      />
      <Routes>
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/"                  element={<Wrap><DashboardPage /></Wrap>} />
        <Route path="/profile"           element={<Wrap><ProfilePage /></Wrap>} />
        <Route path="/recipes"           element={<Wrap><RecipesPage /></Wrap>} />
        <Route path="/recipes/generate"  element={<Wrap><GenerateRecipePage /></Wrap>} />
        <Route path="/meal-plan"         element={<Wrap><MealPlanPage /></Wrap>} />
        <Route path="/meal-log"          element={<Wrap><MealLogPage /></Wrap>} />
        <Route path="/food-camera"       element={<Wrap><FoodCameraPage /></Wrap>} />
        <Route path="/analytics"         element={<Wrap><AnalyticsPage /></Wrap>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ThemeProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
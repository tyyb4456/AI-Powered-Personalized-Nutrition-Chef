// src/pages/RegisterPage.jsx

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import { Loader2, Leaf, Sun, Moon } from 'lucide-react';
import { registerUser } from '../api/auth';
import { useAuth } from '../store/AuthContext';
import { useTheme } from '../store/ThemeContext';

const schema = z.object({
  name: z.string().min(2, 'At least 2 characters'),
  email: z.string().email('Invalid email').optional().or(z.literal('')),
  password: z.string().min(6, 'At least 6 characters'),
  confirmPassword: z.string(),
}).refine(d => d.password === d.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

const RegisterPage = () => {
  const { login } = useAuth();
  const { dark, toggle } = useTheme();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      const payload = { name: data.name, password: data.password, ...(data.email ? { email: data.email } : {}) };
      const response = await registerUser(payload);
      login(response);
      toast.success(`Welcome, ${response.name}!`);
      navigate('/');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const bg = dark ? 'bg-[#080808]' : 'bg-[#f7f6f3]';
  const card = dark ? 'bg-[#111] border-white/8' : 'bg-white border-black/8';
  const label = dark ? 'text-gray-400' : 'text-gray-500';
  const heading = dark ? 'text-white' : 'text-gray-900';
  const input = dark
    ? 'bg-white/4 border-white/8 text-white placeholder-gray-600 focus:border-white/20 focus:bg-white/6'
    : 'bg-black/3 border-black/10 text-gray-900 placeholder-gray-400 focus:border-black/20 focus:bg-white';
  const btn = dark
    ? 'bg-white text-black hover:bg-gray-100 disabled:bg-white/30 disabled:text-white/40'
    : 'bg-gray-900 text-white hover:bg-black disabled:bg-gray-300';
  const linkColor = dark ? 'text-gray-300 hover:text-white' : 'text-gray-700 hover:text-gray-900';
  const mutedLink = dark ? 'text-gray-500' : 'text-gray-400';

  const Field = ({ name, label: lbl, type = 'text', placeholder, hint }) => (
    <div>
      <label className={`block text-xs font-medium mb-2 tracking-wide uppercase ${label}`}>
        {lbl}{hint && <span className={`normal-case ml-1 ${mutedLink}`}>({hint})</span>}
      </label>
      <input
        {...register(name)}
        type={type}
        placeholder={placeholder}
        className={`w-full px-4 py-3 border rounded-xl text-sm outline-none transition-all duration-200 ${input}`}
      />
      {errors[name] && <p className="text-red-400 text-xs mt-1.5">{errors[name].message}</p>}
    </div>
  );

  return (
    <div className={`min-h-screen ${bg} flex items-center justify-center px-4 py-12 transition-colors duration-300`}>

      <button
        onClick={toggle}
        className={`fixed top-5 right-5 p-2.5 rounded-xl border transition-all ${
          dark ? 'border-white/8 text-gray-400 hover:text-white hover:bg-white/8' : 'border-black/8 text-gray-400 hover:text-gray-900 hover:bg-black/5'
        }`}
      >
        {dark ? <Sun size={14} /> : <Moon size={14} />}
      </button>

      <div className={`w-full max-w-sm border rounded-2xl p-8 transition-colors duration-300 ${card}`}>

        <div className="flex items-center gap-2.5 mb-10">
          <div className={`p-2 rounded-xl ${dark ? 'bg-white/8' : 'bg-black/5'}`}>
            <Leaf size={16} className={dark ? 'text-white' : 'text-gray-900'} />
          </div>
          <span className={`text-sm font-semibold tracking-tight ${heading}`}>
            nutrition<span className={mutedLink}>.ai</span>
          </span>
        </div>

        <h1 className={`text-2xl font-bold tracking-tight mb-1 ${heading}`}>Create account</h1>
        <p className={`text-sm mb-8 ${label}`}>Start your nutrition journey</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Field name="name" label="Username" placeholder="choose_a_username" />
          <Field name="email" label="Email" type="email" placeholder="you@example.com" hint="optional" />
          <Field name="password" label="Password" type="password" placeholder="Min 6 characters" />
          <Field name="confirmPassword" label="Confirm Password" type="password" placeholder="Repeat password" />

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-3 rounded-xl text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2 mt-2 ${btn}`}
          >
            {loading && <Loader2 size={14} className="animate-spin" />}
            {loading ? 'Creating…' : 'Create Account'}
          </button>
        </form>

        <p className={`text-sm text-center mt-6 ${label}`}>
          Already have an account?{' '}
          <Link to="/login" className={`font-medium transition-colors ${linkColor}`}>
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;
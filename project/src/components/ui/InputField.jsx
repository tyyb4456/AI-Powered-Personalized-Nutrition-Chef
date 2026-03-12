// src/components/ui/InputField.jsx

import { useTheme } from '../../store/ThemeContext';

const InputField = ({ label, name, register, error, type = 'text', placeholder, hint }) => {
  const { dark } = useTheme();
  return (
    <div>
      <label className={`block text-xs font-medium mb-2 tracking-wide uppercase ${dark ? 'text-gray-400' : 'text-gray-500'}`}>
        {label}
        {hint && <span className={`normal-case ml-1 font-normal ${dark ? 'text-gray-600' : 'text-gray-400'}`}>({hint})</span>}
      </label>
      <input
        {...register(name)}
        type={type}
        placeholder={placeholder}
        className={`w-full px-4 py-3 border rounded-xl text-sm outline-none transition-all duration-200 ${
          dark
            ? 'bg-white/4 border-white/8 text-white placeholder-gray-600 focus:border-white/20 focus:bg-white/6'
            : 'bg-black/3 border-black/10 text-gray-900 placeholder-gray-400 focus:border-black/20 focus:bg-white'
        }`}
      />
      {error && <p className="text-red-400 text-xs mt-1.5">{error.message}</p>}
    </div>
  );
};

export default InputField;
// src/components/ui/SelectField.jsx
import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check } from 'lucide-react';
import { useTheme } from '../../store/ThemeContext';

const SelectField = ({ label, name, register, error, options, placeholder }) => {
  const { dark } = useTheme();
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState('');
  const containerRef = useRef(null);

  const registered = register(name);
  const selectedLabel = options.find(o => o.value === selected)?.label || '';

  const handleSelect = (value) => {
    setSelected(value);
    registered.onChange({ target: { name, value } });
    setOpen(false);
  };

  useEffect(() => {
    const handler = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={containerRef} className="relative">
      {label && (
        <label className={`block text-xs font-medium mb-2 tracking-wide uppercase ${dark ? 'text-gray-400' : 'text-gray-500'}`}>
          {label}
        </label>
      )}

      {/* Hidden input to keep RHF in sync */}
      <input type="hidden" {...registered} value={selected} />

      {/* Trigger button */}
      <div
        onClick={() => setOpen(o => !o)}
        className={`w-full flex items-center justify-between px-4 py-3 border rounded-xl text-sm cursor-pointer transition-all duration-200 select-none ${
          dark
            ? `bg-white/4 border-white/8 text-white hover:border-white/20 ${open ? 'border-white/20 bg-white/6' : ''}`
            : `bg-black/3 border-black/10 text-gray-900 hover:border-black/20 ${open ? 'border-black/20 bg-white' : ''}`
        }`}
      >
        <span className={!selected ? (dark ? 'text-gray-600' : 'text-gray-400') : ''}>
          {selected ? selectedLabel : (placeholder || 'Select…')}
        </span>
        <ChevronDown
          size={14}
          className={`transition-transform duration-200 shrink-0 ${dark ? 'text-gray-500' : 'text-gray-400'} ${open ? 'rotate-180' : ''}`}
        />
      </div>

      {/* Custom dropdown panel */}
      {open && (
        <div className={`absolute z-50 w-full mt-1.5 border rounded-xl overflow-hidden shadow-2xl ${
          dark
            ? 'bg-[#1c1c1c] border-white/10 shadow-black/70'
            : 'bg-white border-black/10 shadow-black/10'
        }`}>
          {/* Placeholder row */}
          <button
            type="button"
            onClick={() => handleSelect('')}
            className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${
              dark ? 'text-gray-600 hover:bg-white/5' : 'text-gray-400 hover:bg-black/3'
            }`}
          >
            {placeholder || 'Select…'}
          </button>

          <div className={`h-px mx-3 ${dark ? 'bg-white/6' : 'bg-black/6'}`} />

          {/* Option rows */}
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => handleSelect(opt.value)}
              className={`w-full flex items-center justify-between px-4 py-2.5 text-sm transition-colors ${
                selected === opt.value
                  ? dark
                    ? 'bg-white/8 text-white'
                    : 'bg-black/5 text-gray-900'
                  : dark
                    ? 'text-gray-300 hover:bg-white/5 hover:text-white'
                    : 'text-gray-700 hover:bg-black/3 hover:text-gray-900'
              }`}
            >
              <span>{opt.label}</span>
              {selected === opt.value && (
                <Check size={11} className={dark ? 'text-white/50' : 'text-gray-400'} />
              )}
            </button>
          ))}
        </div>
      )}

      {error && <p className="text-red-400 text-xs mt-1.5">{error.message}</p>}
    </div>
  );
};

export default SelectField;
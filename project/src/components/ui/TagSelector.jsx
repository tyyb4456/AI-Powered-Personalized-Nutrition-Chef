// src/components/ui/TagSelector.jsx

import { useTheme } from '../../store/ThemeContext';
import { X } from 'lucide-react';

const TagSelector = ({ label, options, selected, onChange }) => {
  const { dark } = useTheme();

  const toggle = (value) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  return (
    <div>
      {label && (
        <label className={`block text-xs font-medium mb-3 tracking-wide uppercase ${dark ? 'text-gray-400' : 'text-gray-500'}`}>
          {label}
        </label>
      )}

      {/* All options as toggleable pills */}
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => {
          const isSelected = selected.includes(opt.value);
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => toggle(opt.value)}
              className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border font-medium transition-all duration-200 ${
                isSelected
                  ? dark
                    ? 'bg-white text-black border-white'
                    : 'bg-gray-900 text-white border-gray-900'
                  : dark
                    ? 'bg-white/4 text-gray-400 border-white/8 hover:border-white/20 hover:text-white'
                    : 'bg-transparent text-gray-500 border-black/10 hover:border-black/25 hover:text-gray-900'
              }`}
            >
              {opt.label}
              {isSelected && (
                <X size={10} className={dark ? 'text-black/50' : 'text-white/60'} />
              )}
            </button>
          );
        })}
      </div>

      {/* Selected count */}
      {selected.length > 0 && (
        <p className={`text-xs mt-3 ${dark ? 'text-gray-600' : 'text-gray-400'}`}>
          {selected.length} selected
        </p>
      )}
    </div>
  );
};

export default TagSelector;
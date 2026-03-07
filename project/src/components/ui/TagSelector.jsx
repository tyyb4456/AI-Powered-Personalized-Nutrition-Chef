// src/components/ui/TagSelector.jsx

import { useState } from 'react';
import { X } from 'lucide-react';

const TagSelector = ({ label, options, selected, onChange }) => {
  const [open, setOpen] = useState(false);

  const toggle = (value) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>

      {/* Selected tags */}
      <div className="flex flex-wrap gap-2 mb-2">
        {selected.map((val) => (
          <span
            key={val}
            className="inline-flex items-center gap-1 bg-primary-100 text-primary-700 text-xs px-2.5 py-1 rounded-full"
          >
            {val}
            <button type="button" onClick={() => toggle(val)}>
              <X size={12} />
            </button>
          </span>
        ))}
        {selected.length === 0 && (
          <span className="text-sm text-gray-400">None selected</span>
        )}
      </div>

      {/* Toggle options */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="text-sm text-primary-600 hover:underline"
      >
        {open ? 'Hide options' : 'Select options'}
      </button>

      {open && (
        <div className="mt-2 flex flex-wrap gap-2">
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => toggle(opt.value)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                selected.includes(opt.value)
                  ? 'bg-primary-600 text-white border-primary-600'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-primary-400'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default TagSelector;
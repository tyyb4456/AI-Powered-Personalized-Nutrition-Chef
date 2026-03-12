// src/components/recipe/StarRating.jsx
import { useState } from 'react';
import { Star } from 'lucide-react';
import { useTheme } from '../../store/ThemeContext';

const StarRating = ({ onRate, disabled }) => {
  const { dark } = useTheme();
  const [hovered, setHovered]   = useState(0);
  const [selected, setSelected] = useState(0);

  const handleClick = (val) => {
    if (disabled) return;
    setSelected(val);
    onRate(val);
  };

  return (
    <div className="flex items-center gap-1.5">
      {[1, 2, 3, 4, 5].map((star) => {
        const active = star <= (hovered || selected);
        return (
          <button
            key={star}
            type="button"
            disabled={disabled}
            onClick={() => handleClick(star)}
            onMouseEnter={() => setHovered(star)}
            onMouseLeave={() => setHovered(0)}
            className="transition-transform hover:scale-110 disabled:cursor-default"
          >
            <Star
              size={22}
              className={`transition-colors duration-150 ${
                active
                  ? 'fill-amber-400 text-amber-400'
                  : dark
                    ? 'text-white/15 fill-transparent'
                    : 'text-black/15 fill-transparent'
              }`}
            />
          </button>
        );
      })}
    </div>
  );
};

export default StarRating;
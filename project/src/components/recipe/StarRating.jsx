// src/components/recipe/StarRating.jsx

import { useState } from 'react';
import { Star } from 'lucide-react';

const StarRating = ({ onRate, disabled }) => {
  const [hovered, setHovered] = useState(0);
  const [selected, setSelected] = useState(0);

  const handleClick = (val) => {
    if (disabled) return;
    setSelected(val);
    onRate(val);
  };

  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
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
            size={24}
            className={`transition-colors ${
              star <= (hovered || selected)
                ? 'fill-amber-400 text-amber-400'
                : 'text-gray-300'
            }`}
          />
        </button>
      ))}
    </div>
  );
};

export default StarRating;
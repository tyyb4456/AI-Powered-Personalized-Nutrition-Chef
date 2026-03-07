// src/components/recipe/MacroBadge.jsx

const colors = {
  calories: 'bg-amber-50 text-amber-700 border-amber-200',
  protein:  'bg-blue-50 text-blue-700 border-blue-200',
  carbs:    'bg-orange-50 text-orange-700 border-orange-200',
  fat:      'bg-purple-50 text-purple-700 border-purple-200',
  fiber:    'bg-green-50 text-green-700 border-green-200',
};

const MacroBadge = ({ label, value, unit, type }) => {
  return (
    <div className={`flex flex-col items-center px-4 py-3 rounded-xl border ${colors[type] || 'bg-gray-50 text-gray-700 border-gray-200'}`}>
      <span className="text-lg font-bold">
        {value}
        <span className="text-xs font-normal ml-0.5">{unit}</span>
      </span>
      <span className="text-xs mt-0.5 opacity-80">{label}</span>
    </div>
  );
};

export default MacroBadge;
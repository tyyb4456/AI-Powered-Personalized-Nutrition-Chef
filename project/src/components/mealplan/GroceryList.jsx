// src/components/mealplan/GroceryList.jsx

import { ShoppingCart, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getGroceryList } from '../../api/mealPlans';

const GroceryList = ({ planId }) => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['grocery', planId],
    queryFn: () => getGroceryList(planId),
    enabled: !!planId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="animate-spin text-primary-600" size={24} />
      </div>
    );
  }

  if (isError) {
    return (
      <p className="text-sm text-red-500 text-center py-8">
        Failed to load grocery list.
      </p>
    );
  }

  const categories = data?.categories || {};
  const hasItems = Object.keys(categories).length > 0;

  // Flat list fallback if backend returns items array
  const flatItems = data?.items || [];

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <ShoppingCart size={18} className="text-primary-600" />
        <h3 className="text-base font-semibold text-gray-900">Grocery List</h3>
        {data?.estimated_total_pkr && (
          <span className="ml-auto text-sm font-medium text-green-700 bg-green-50 border border-green-200 px-3 py-1 rounded-full">
            ~PKR {data.estimated_total_pkr}
          </span>
        )}
      </div>

      {hasItems ? (
        Object.entries(categories).map(([category, items]) => (
          <div key={category}>
            <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
              {category}
            </h4>
            <ul className="space-y-1.5">
              {(Array.isArray(items) ? items : []).map((item, i) => (
                <li key={i} className="flex items-center justify-between text-sm bg-white border border-gray-100 rounded-lg px-3 py-2">
                  <span className="text-gray-800">{item.name || item}</span>
                  {item.quantity && (
                    <span className="text-gray-400 text-xs">{item.quantity}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))
      ) : flatItems.length > 0 ? (
        <ul className="space-y-1.5">
          {flatItems.map((item, i) => (
            <li key={i} className="flex items-center justify-between text-sm bg-white border border-gray-100 rounded-lg px-3 py-2">
              <span className="text-gray-800">{item.name || item}</span>
              {item.quantity && (
                <span className="text-gray-400 text-xs">{item.quantity}</span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-gray-400 text-center py-8">No grocery items found.</p>
      )}
    </div>
  );
};

export default GroceryList;
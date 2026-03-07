// src/components/meallog/LogMealForm.jsx

import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2, PlusCircle } from 'lucide-react';
import InputField from '../ui/InputField';
import SelectField from '../ui/SelectField';

const schema = z.object({
  dish_name: z.string().min(1, 'Dish name is required'),
  meal_slot: z.string().min(1, 'Select a meal slot'),
  calories:  z.coerce.number().min(0).max(5000),
  protein_g: z.coerce.number().min(0),
  carbs_g:   z.coerce.number().min(0),
  fat_g:     z.coerce.number().min(0),
});

const LogMealForm = ({ date, onSuccess, defaultValues }) => {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: defaultValues || {},
  });

  const onSubmit = async (data) => {
    await onSuccess({
      ...data,
      log_date: date,
      source: 'manual',
    });
    reset();
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

      {/* Dish name */}
      <InputField
        label="Dish Name"
        name="dish_name"
        register={register}
        error={errors.dish_name}
        placeholder="e.g. Chicken Karahi"
      />

      {/* Meal slot */}
      <SelectField
        label="Meal Slot"
        name="meal_slot"
        register={register}
        error={errors.meal_slot}
        options={[
          { value: 'breakfast', label: '🌅 Breakfast' },
          { value: 'lunch',     label: '☀️ Lunch' },
          { value: 'dinner',    label: '🌙 Dinner' },
          { value: 'snack',     label: '🍎 Snack' },
        ]}
      />

      {/* Macros row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <InputField
          label="Calories"
          name="calories"
          type="number"
          placeholder="0"
          hint="kcal"
          register={register}
          error={errors.calories}
        />
        <InputField
          label="Protein"
          name="protein_g"
          type="number"
          placeholder="0"
          hint="g"
          register={register}
          error={errors.protein_g}
        />
        <InputField
          label="Carbs"
          name="carbs_g"
          type="number"
          placeholder="0"
          hint="g"
          register={register}
          error={errors.carbs_g}
        />
        <InputField
          label="Fat"
          name="fat_g"
          type="number"
          placeholder="0"
          hint="g"
          register={register}
          error={errors.fat_g}
        />
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2.5 rounded-lg text-sm transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
      >
        {isSubmitting
          ? <Loader2 size={15} className="animate-spin" />
          : <PlusCircle size={15} />
        }
        {isSubmitting ? 'Logging...' : 'Log Meal'}
      </button>
    </form>
  );
};

export default LogMealForm;
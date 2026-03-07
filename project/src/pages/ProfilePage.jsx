// src/pages/ProfilePage.jsx

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import { Loader2, User, Save } from 'lucide-react';
import { getMyProfile, updateMyProfile } from '../api/users';
import InputField from '../components/ui/InputField';
import SelectField from '../components/ui/SelectField';
import TagSelector from '../components/ui/TagSelector';

const schema = z.object({
  age: z.coerce.number().min(1).max(120).optional().or(z.literal('')),
  gender: z.string().optional(),
  weight_kg: z.coerce.number().min(20).max(300).optional().or(z.literal('')),
  height_cm: z.coerce.number().min(50).max(250).optional().or(z.literal('')),
  activity_level: z.string().optional(),
  fitness_goal: z.string().optional(),
  cuisine: z.string().optional(),
  spice_level: z.string().optional(),
});

const ALLERGY_OPTIONS = [
  { value: 'nuts', label: '🥜 Nuts' },
  { value: 'dairy', label: '🥛 Dairy' },
  { value: 'gluten', label: '🌾 Gluten' },
  { value: 'eggs', label: '🥚 Eggs' },
  { value: 'seafood', label: '🦐 Seafood' },
  { value: 'soy', label: '🫘 Soy' },
  { value: 'shellfish', label: '🦞 Shellfish' },
];

const CONDITION_OPTIONS = [
  { value: 'diabetes', label: 'Diabetes' },
  { value: 'hypertension', label: 'Hypertension' },
  { value: 'celiac', label: 'Celiac' },
  { value: 'lactose_intolerance', label: 'Lactose Intolerance' },
  { value: 'kidney_disease', label: 'Kidney Disease' },
  { value: 'heart_disease', label: 'Heart Disease' },
  { value: 'ibs', label: 'IBS' },
  { value: 'anemia', label: 'Anemia' },
  { value: 'osteoporosis', label: 'Osteoporosis' },
];

const ProfilePage = () => {
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [allergies, setAllergies] = useState([]);
  const [conditions, setConditions] = useState([]);

  const { register, handleSubmit, reset, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  });

  // Load existing profile
  useEffect(() => {
    const load = async () => {
      try {
        const data = await getMyProfile();
        reset({
          age: data.age || '',
          gender: data.gender || '',
          weight_kg: data.weight_kg || '',
          height_cm: data.height_cm || '',
          activity_level: data.activity_level || '',
          fitness_goal: data.fitness_goal || '',
          cuisine: data.cuisine || '',
          spice_level: data.spice_level || '',
        });
        setAllergies(data.allergies || []);
        setConditions(data.medical_conditions || []);
      } catch {
        toast.error('Failed to load profile');
      } finally {
        setFetching(false);
      }
    };
    load();
  }, [reset]);

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      // Clean up empty strings to undefined
      const payload = Object.fromEntries(
        Object.entries(data).filter(([, v]) => v !== '' && v !== undefined)
      );
      payload.allergies = allergies;
      payload.medical_conditions = conditions;

      await updateMyProfile(payload);
      toast.success('Profile saved successfully!');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to save profile.';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-primary-600" size={32} />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-50 rounded-lg">
          <User className="text-primary-600" size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Profile</h1>
          <p className="text-sm text-gray-500">Your health data powers the AI recommendations</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">

        {/* Physical Stats */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Physical Stats</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <InputField
              label="Age"
              name="age"
              type="number"
              placeholder="e.g. 25"
              register={register}
              error={errors.age}
            />
            <SelectField
              label="Gender"
              name="gender"
              register={register}
              error={errors.gender}
              options={[
                { value: 'male', label: 'Male' },
                { value: 'female', label: 'Female' },
                { value: 'other', label: 'Other' },
              ]}
            />
            <InputField
              label="Weight"
              name="weight_kg"
              type="number"
              placeholder="e.g. 70"
              hint="kg"
              register={register}
              error={errors.weight_kg}
            />
            <InputField
              label="Height"
              name="height_cm"
              type="number"
              placeholder="e.g. 170"
              hint="cm"
              register={register}
              error={errors.height_cm}
            />
          </div>
        </div>

        {/* Goals & Activity */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Goals & Activity</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <SelectField
              label="Activity Level"
              name="activity_level"
              register={register}
              error={errors.activity_level}
              options={[
                { value: 'sedentary', label: 'Sedentary (desk job)' },
                { value: 'light', label: 'Light (1-3 days/week)' },
                { value: 'moderate', label: 'Moderate (3-5 days/week)' },
                { value: 'active', label: 'Active (6-7 days/week)' },
                { value: 'very_active', label: 'Very Active (athlete)' },
              ]}
            />
            <SelectField
              label="Fitness Goal"
              name="fitness_goal"
              register={register}
              error={errors.fitness_goal}
              options={[
                { value: 'fat_loss', label: 'Fat Loss' },
                { value: 'muscle_gain', label: 'Muscle Gain' },
                { value: 'maintenance', label: 'Maintenance' },
              ]}
            />
          </div>
        </div>

        {/* Food Preferences */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Food Preferences</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <SelectField
              label="Cuisine Preference"
              name="cuisine"
              register={register}
              error={errors.cuisine}
              options={[
                { value: 'pakistani', label: '🇵🇰 Pakistani' },
                { value: 'indian', label: '🇮🇳 Indian' },
                { value: 'mediterranean', label: '🫒 Mediterranean' },
                { value: 'chinese', label: '🇨🇳 Chinese' },
                { value: 'italian', label: '🇮🇹 Italian' },
                { value: 'american', label: '🇺🇸 American' },
                { value: 'any', label: '🌍 Any' },
              ]}
            />
            <SelectField
              label="Spice Level"
              name="spice_level"
              register={register}
              error={errors.spice_level}
              options={[
                { value: 'mild', label: '🟢 Mild' },
                { value: 'medium', label: '🟡 Medium' },
                { value: 'hot', label: '🔴 Hot' },
                { value: 'extra_hot', label: '🌶️ Extra Hot' },
              ]}
            />
          </div>
        </div>

        {/* Allergies */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Allergies & Restrictions</h2>
          <TagSelector
            label="Food Allergies"
            options={ALLERGY_OPTIONS}
            selected={allergies}
            onChange={setAllergies}
          />
        </div>

        {/* Medical Conditions */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Medical Conditions</h2>
          <TagSelector
            label="Conditions (affects recipe generation)"
            options={CONDITION_OPTIONS}
            selected={conditions}
            onChange={setConditions}
          />
        </div>

        {/* Save Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-3 rounded-lg text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Save size={16} />
          )}
          {loading ? 'Saving...' : 'Save Profile'}
        </button>
      </form>
    </div>
  );
};

export default ProfilePage;
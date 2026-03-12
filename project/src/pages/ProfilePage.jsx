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
import { useTheme } from '../store/ThemeContext';

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
  { value: 'nuts',      label: '🥜 Nuts' },
  { value: 'dairy',     label: '🥛 Dairy' },
  { value: 'gluten',    label: '🌾 Gluten' },
  { value: 'eggs',      label: '🥚 Eggs' },
  { value: 'seafood',   label: '🦐 Seafood' },
  { value: 'soy',       label: '🫘 Soy' },
  { value: 'shellfish', label: '🦞 Shellfish' },
];

const CONDITION_OPTIONS = [
  { value: 'diabetes',           label: 'Diabetes' },
  { value: 'hypertension',       label: 'Hypertension' },
  { value: 'celiac',             label: 'Celiac' },
  { value: 'lactose_intolerance',label: 'Lactose Intolerance' },
  { value: 'kidney_disease',     label: 'Kidney Disease' },
  { value: 'heart_disease',      label: 'Heart Disease' },
  { value: 'ibs',                label: 'IBS' },
  { value: 'anemia',             label: 'Anemia' },
  { value: 'osteoporosis',       label: 'Osteoporosis' },
];

const SELECT_OPTIONS = {
  gender: [{ value: 'male', label: 'Male' }, { value: 'female', label: 'Female' }, { value: 'other', label: 'Other' }],
  activity_level: [
    { value: 'sedentary',    label: 'Sedentary' },
    { value: 'light',        label: 'Light' },
    { value: 'moderate',     label: 'Moderate' },
    { value: 'active',       label: 'Active' },
    { value: 'very_active',  label: 'Very Active' },
  ],
  fitness_goal: [
    { value: 'weight_loss',   label: 'Weight Loss' },
    { value: 'muscle_gain',   label: 'Muscle Gain' },
    { value: 'maintenance',   label: 'Maintenance' },
    { value: 'endurance',     label: 'Endurance' },
  ],
  spice_level: [
    { value: 'mild',   label: 'Mild' },
    { value: 'medium', label: 'Medium' },
    { value: 'hot',    label: 'Hot' },
    { value: 'extra',  label: 'Extra Hot' },
  ],
};

const ProfilePage = () => {
  const { dark } = useTheme();
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [allergies, setAllergies] = useState([]);
  const [conditions, setConditions] = useState([]);

  const { register, handleSubmit, reset, formState: { errors } } = useForm({ resolver: zodResolver(schema) });

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getMyProfile();
        reset({
          age: data.age || '', gender: data.gender || '',
          weight_kg: data.weight_kg || '', height_cm: data.height_cm || '',
          activity_level: data.activity_level || '', fitness_goal: data.fitness_goal || '',
          cuisine: data.cuisine || '', spice_level: data.spice_level || '',
        });
        setAllergies(data.allergies || []);
        setConditions(data.medical_conditions || []);
      } catch { toast.error('Failed to load profile'); }
      finally { setFetching(false); }
    };
    load();
  }, [reset]);

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      await updateMyProfile({ ...data, allergies, medical_conditions: conditions });
      toast.success('Profile saved');
    } catch { toast.error('Failed to save profile'); }
    finally { setLoading(false); }
  };

  const text  = dark ? 'text-white' : 'text-gray-900';
  const muted = dark ? 'text-gray-500' : 'text-gray-400';
  const card  = dark ? 'bg-white/4 border-white/8' : 'bg-white border-black/8';
  const sectionLabel = `text-xs font-medium tracking-widest uppercase mb-5 block ${muted}`;
  const divider = dark ? 'border-white/6' : 'border-black/6';

  if (fetching) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className={`animate-spin ${dark ? 'text-white/30' : 'text-gray-300'}`} size={22} />
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-3">
          <div className={`p-2 rounded-xl ${dark ? 'bg-white/8' : 'bg-black/5'}`}>
            <User size={15} className={text} />
          </div>
          <span className={`text-xs font-medium tracking-widest uppercase ${muted}`}>Profile</span>
        </div>
        <h1 className={`text-3xl font-bold tracking-tight ${text}`}>Your Profile</h1>
        <p className={`text-sm mt-1 ${muted}`}>Personalize AI meal suggestions to match your goals</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

        {/* Body stats */}
        <div className={`rounded-2xl border p-6 ${card}`}>
          <span className={sectionLabel}>Body Stats</span>
          <div className="grid grid-cols-2 gap-4">
            <InputField label="Age"    name="age"       register={register} error={errors.age}       type="number" placeholder="25" />
            <SelectField label="Gender" name="gender"   register={register} error={errors.gender}    options={SELECT_OPTIONS.gender} placeholder="Select" />
            <InputField label="Weight" name="weight_kg" register={register} error={errors.weight_kg} type="number" placeholder="70" hint="kg" />
            <InputField label="Height" name="height_cm" register={register} error={errors.height_cm} type="number" placeholder="175" hint="cm" />
          </div>
        </div>

        {/* Goals */}
        <div className={`rounded-2xl border p-6 ${card}`}>
          <span className={sectionLabel}>Goals & Activity</span>
          <div className="grid grid-cols-2 gap-4">
            <SelectField label="Activity Level" name="activity_level" register={register} options={SELECT_OPTIONS.activity_level} placeholder="Select" />
            <SelectField label="Fitness Goal"   name="fitness_goal"   register={register} options={SELECT_OPTIONS.fitness_goal}   placeholder="Select" />
          </div>
        </div>

        {/* Preferences */}
        <div className={`rounded-2xl border p-6 ${card}`}>
          <span className={sectionLabel}>Food Preferences</span>
          <div className="grid grid-cols-2 gap-4">
            <InputField  label="Cuisine"    name="cuisine"     register={register} placeholder="e.g. Pakistani" />
            <SelectField label="Spice Level" name="spice_level" register={register} options={SELECT_OPTIONS.spice_level} placeholder="Select" />
          </div>
        </div>

        {/* Allergies */}
        <div className={`rounded-2xl border p-6 ${card}`}>
          <span className={sectionLabel}>Allergies</span>
          <TagSelector selected={allergies} onChange={setAllergies} options={ALLERGY_OPTIONS} dark={dark} />
        </div>

        {/* Conditions */}
        <div className={`rounded-2xl border p-6 ${card}`}>
          <span className={sectionLabel}>Medical Conditions</span>
          <TagSelector selected={conditions} onChange={setConditions} options={CONDITION_OPTIONS} dark={dark} />
        </div>

        <button
          type="submit"
          disabled={loading}
          className={`w-full py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all duration-200 ${
            dark ? 'bg-white text-black hover:bg-gray-100 disabled:opacity-30' : 'bg-gray-900 text-white hover:bg-black disabled:opacity-40'
          }`}
        >
          {loading ? <><Loader2 size={14} className="animate-spin" />Saving…</> : <><Save size={14} />Save Profile</>}
        </button>
      </form>
    </div>
  );
};

export default ProfilePage;
// src/components/image/ImageDropzone.jsx
import { useCallback, useState } from 'react';
import { Camera, Upload, X, Image } from 'lucide-react';
import { useTheme } from '../../store/ThemeContext';

const ImageDropzone = ({ onImageReady, disabled }) => {
  const { dark } = useTheme();
  const [preview, setPreview]   = useState(null);
  const [dragging, setDragging] = useState(false);

  const processFile = useCallback((file) => {
    if (!file) return;
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) { alert('Please upload a JPEG, PNG or WebP image.'); return; }
    if (file.size > 10 * 1024 * 1024)   { alert('Image must be under 10MB.'); return; }
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target.result;
      const base64  = dataUrl.split(',')[1];
      setPreview(dataUrl);
      onImageReady({ base64, mime_type: file.type, dataUrl });
    };
    reader.readAsDataURL(file);
  }, [onImageReady]);

  const handleDrop = useCallback((e) => {
    e.preventDefault(); setDragging(false);
    processFile(e.dataTransfer.files[0]);
  }, [processFile]);

  const handleFileInput = (e) => processFile(e.target.files[0]);
  const clearImage      = () => { setPreview(null); onImageReady(null); };

  // Preview state
  if (preview) {
    return (
      <div className={`relative rounded-2xl overflow-hidden border ${dark ? 'border-white/8' : 'border-black/8'}`}>
        <img src={preview} alt="Food preview" className="w-full max-h-72 object-cover" />
        {!disabled && (
          <button
            onClick={clearImage}
            className={`absolute top-3 right-3 rounded-full p-1.5 shadow-md transition-colors ${
              dark ? 'bg-black/60 hover:bg-black/80 text-white' : 'bg-white hover:bg-red-50 text-gray-600'
            }`}
          >
            <X size={16} />
          </button>
        )}
      </div>
    );
  }

  // Dropzone
  const draggingCls = dark
    ? 'border-white/30 bg-white/8'
    : 'border-black/25 bg-black/5';
  const idleCls = dark
    ? 'border-white/10 bg-white/3 hover:border-white/20 hover:bg-white/5'
    : 'border-black/10 bg-black/2 hover:border-black/20 hover:bg-black/4';

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true);  }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`relative border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-200 ${
        dragging ? draggingCls : idleCls
      }`}
    >
      <div className="flex flex-col items-center gap-3">
        {/* Icon */}
        <div className={`p-4 rounded-full border ${
          dark ? 'bg-white/6 border-white/10' : 'bg-black/4 border-black/8'
        }`}>
          <Image size={28} className={dark ? 'text-gray-500' : 'text-gray-400'} />
        </div>

        {/* Text */}
        <div>
          <p className={`text-sm font-semibold ${dark ? 'text-gray-200' : 'text-gray-700'}`}>
            Drop your food photo here
          </p>
          <p className={`text-xs mt-1 ${dark ? 'text-gray-600' : 'text-gray-400'}`}>
            JPEG, PNG or WebP · Max 10MB
          </p>
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-3 mt-1">
          <label className={`flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-xl border cursor-pointer transition-all duration-200 ${
            dark
              ? 'bg-white/6 border-white/10 text-gray-300 hover:border-white/20 hover:bg-white/10'
              : 'bg-white border-black/12 text-gray-600 hover:border-black/20 hover:bg-gray-50'
          }`}>
            <Upload size={14} />
            Browse file
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handleFileInput} className="hidden" />
          </label>

          <label className={`flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-xl cursor-pointer transition-all duration-200 ${
            dark
              ? 'bg-white text-black hover:bg-gray-100'
              : 'bg-gray-900 text-white hover:bg-black'
          }`}>
            <Camera size={14} />
            Take photo
            <input type="file" accept="image/*" capture="environment" onChange={handleFileInput} className="hidden" />
          </label>
        </div>
      </div>
    </div>
  );
};

export default ImageDropzone;
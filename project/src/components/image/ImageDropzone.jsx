// src/components/image/ImageDropzone.jsx

import { useCallback, useState } from 'react';
import { Camera, Upload, X, Image } from 'lucide-react';

const ImageDropzone = ({ onImageReady, disabled }) => {
  const [preview, setPreview]   = useState(null);
  const [dragging, setDragging] = useState(false);

  const processFile = useCallback((file) => {
    if (!file) return;

    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      alert('Please upload a JPEG, PNG or WebP image.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      alert('Image must be under 10MB.');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl   = e.target.result;
      const base64    = dataUrl.split(',')[1];
      setPreview(dataUrl);
      onImageReady({ base64, mime_type: file.type, dataUrl });
    };
    reader.readAsDataURL(file);
  }, [onImageReady]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    processFile(file);
  }, [processFile]);

  const handleFileInput = (e) => {
    processFile(e.target.files[0]);
  };

  const clearImage = () => {
    setPreview(null);
    onImageReady(null);
  };

  if (preview) {
    return (
      <div className="relative rounded-xl overflow-hidden border border-gray-200">
        <img
          src={preview}
          alt="Food preview"
          className="w-full max-h-72 object-cover"
        />
        {!disabled && (
          <button
            onClick={clearImage}
            className="absolute top-3 right-3 bg-white rounded-full p-1.5 shadow-md hover:bg-red-50 transition-colors"
          >
            <X size={16} className="text-gray-600" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true);  }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
        dragging
          ? 'border-primary-400 bg-primary-50'
          : 'border-gray-300 bg-gray-50 hover:border-primary-300 hover:bg-primary-50/30'
      }`}
    >
      <div className="flex flex-col items-center gap-3">
        <div className="p-4 bg-white rounded-full shadow-sm border border-gray-200">
          <Image size={28} className="text-gray-400" />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-700">Drop your food photo here</p>
          <p className="text-xs text-gray-400 mt-1">JPEG, PNG or WebP · Max 10MB</p>
        </div>

        <div className="flex items-center gap-3 mt-1">
          {/* File upload */}
          <label className="flex items-center gap-2 bg-white border border-gray-300 hover:border-primary-400 text-sm text-gray-600 font-medium px-4 py-2 rounded-lg cursor-pointer transition-colors">
            <Upload size={14} />
            Browse file
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileInput}
              className="hidden"
            />
          </label>

          {/* Camera capture (mobile) */}
          <label className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium px-4 py-2 rounded-lg cursor-pointer transition-colors">
            <Camera size={14} />
            Take photo
            <input
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileInput}
              className="hidden"
            />
          </label>
        </div>
      </div>
    </div>
  );
};

export default ImageDropzone;
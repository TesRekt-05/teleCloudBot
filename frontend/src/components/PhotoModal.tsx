// frontend/src/components/PhotoModal.tsx
import { useState } from 'react';
import { File as FileType } from '../api/api';

interface PhotoModalProps {
  file: FileType;
  fileUrl: string;
  onClose: () => void;
  onDelete: () => void;
}

export const PhotoModal = ({ file, fileUrl, onClose, onDelete }: PhotoModalProps) => {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDownload = () => {
    // Create a temporary link and trigger download
    const link = document.createElement('a');
    link.href = fileUrl;
    link.download = file.name;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDelete = async () => {
    if (window.confirm(`Delete "${file.name}"?`)) {
      setIsDeleting(true);
      await onDelete();
      onClose();
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(2)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="relative max-w-4xl max-h-full flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 bg-red-500 text-white rounded-full w-10 h-10 flex items-center justify-center hover:bg-red-600 transition z-10"
        >
          ✕
        </button>

        {/* Image */}
        <img
          src={fileUrl}
          alt={file.name}
          className="max-w-full max-h-[70vh] object-contain rounded-lg"
        />

        {/* Info panel */}
        <div className="bg-white rounded-b-lg p-4 mt-2">
          <h3 className="font-bold text-lg mb-2">{file.name}</h3>
          <p className="text-gray-600 text-sm mb-4">
            {formatFileSize(file.size)} • {new Date(file.uploaded_at).toLocaleDateString()}
          </p>

          {/* Action buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleDownload}
              className="flex-1 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition flex items-center justify-center gap-2"
            >
              <span>📥</span> Download
            </button>
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              className="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <span>🗑️</span> {isDeleting ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

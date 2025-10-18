// frontend/src/components/FileGallery.tsx
import { useState, useEffect } from 'react';
import { File as FileType, getFolderFiles, deleteFile, getFileUrl } from '../api/api';
import { PhotoModal } from '../components/PhotoModal';

interface FileGalleryProps {
  folderId: number;
  folderName: string;
  onBack: () => void;
}

export const FileGallery = ({ folderId, folderName, onBack }: FileGalleryProps) => {
  const [files, setFiles] = useState<FileType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileType | null>(null);
  const [selectedFileUrl, setSelectedFileUrl] = useState<string | null>(null);
  const [loadingUrls, setLoadingUrls] = useState<Record<number, string>>({});

  useEffect(() => {
    loadFiles();
  }, [folderId]);

  const loadFiles = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getFolderFiles(folderId);
      setFiles(data);

      // Preload URLs for photos
      data.forEach(async (file) => {
        if (file.type === 'photo') {
          try {
            const url = await getFileUrl(file.id);
            setLoadingUrls((prev) => ({ ...prev, [file.id]: url }));
          } catch (err) {
            console.error(`Failed to load URL for file ${file.id}:`, err);
          }
        }
      });
    } catch (err) {
      setError('Failed to load files');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileClick = async (file: FileType) => {
    try {
      // Get file URL if not already loaded
      const url = loadingUrls[file.id] || (await getFileUrl(file.id));
      setSelectedFileUrl(url);
      setSelectedFile(file);
    } catch (err) {
      console.error('Failed to load file:', err);
      alert('Failed to load file preview');
    }
  };

  const handleDelete = async (fileId: number) => {
    try {
      await deleteFile(fileId);
      setFiles(files.filter((f) => f.id !== fileId));
    } catch (err) {
      console.error('Failed to delete file:', err);
      alert('Failed to delete file');
    }
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'photo':
        return '🖼️';
      case 'video':
        return '🎥';
      case 'audio':
        return '🎵';
      case 'document':
        return '📄';
      default:
        return '📎';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(2)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-2">⏳</div>
          <p className="text-gray-600">Loading files...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={onBack}
          className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded-lg transition"
        >
          ← Back
        </button>
        <h2 className="text-2xl font-bold">📁 {folderName}</h2>
        <span className="text-gray-500">({files.length} files)</span>
      </div>

      {/* Files Grid */}
      {files.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">No files in this folder</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {files.map((file) => (
            <div
              key={file.id}
              className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition cursor-pointer"
              onClick={() => handleFileClick(file)}
            >
              {/* Thumbnail */}
              <div className="aspect-square bg-gray-100 flex items-center justify-center overflow-hidden">
                {file.type === 'photo' && loadingUrls[file.id] ? (
                  <img
                    src={loadingUrls[file.id]}
                    alt={file.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-6xl">{getFileIcon(file.type)}</span>
                )}
              </div>

              {/* File info */}
              <div className="p-3">
                <p className="text-sm font-medium truncate mb-1">{file.name}</p>
                <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
              </div>

              {/* Delete button */}
              <div className="px-3 pb-3">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm(`Delete "${file.name}"?`)) {
                      handleDelete(file.id);
                    }
                  }}
                  className="w-full bg-red-500 text-white text-sm py-1 rounded hover:bg-red-600 transition"
                >
                  🗑️ Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Photo Modal */}
      {selectedFile && selectedFileUrl && (
        <PhotoModal
          file={selectedFile}
          fileUrl={selectedFileUrl}
          onClose={() => {
            setSelectedFile(null);
            setSelectedFileUrl(null);
          }}
          onDelete={() => handleDelete(selectedFile.id)}
        />
      )}
    </div>
  );
};

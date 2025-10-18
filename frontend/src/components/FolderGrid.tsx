// frontend/src/components/FolderGrid.tsx
import React from 'react';
import type { Folder } from '../api/api';

interface FolderGridProps {
  folders: Folder[];
  onFolderClick: (folderId: number) => void;
  onDeleteFolder: (folderId: number) => void;
}

const FolderGrid: React.FC<FolderGridProps> = ({ folders, onFolderClick, onDeleteFolder }) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 p-4">
      {folders.map((folder) => (
        <div
          key={folder.id}
          className="bg-white rounded-lg shadow-md hover:shadow-xl transition-shadow duration-300 overflow-hidden"
        >
          <div
            onClick={() => onFolderClick(folder.id)}
            className="p-6 cursor-pointer hover:bg-gray-50"
          >
            <div className="flex flex-col items-center">
              <svg
                className="w-16 h-16 text-blue-500 mb-3"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
              </svg>
              <h3 className="font-semibold text-gray-800 text-center truncate w-full">
                {folder.name}
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                {folder.file_count} files
              </p>
            </div>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (confirm(`Delete folder "${folder.name}" and all its files?`)) {
                onDeleteFolder(folder.id);
              }
            }}
            className="w-full bg-red-500 hover:bg-red-600 text-white py-2 text-sm font-medium transition-colors"
          >
            🗑️ Delete
          </button>
        </div>
      ))}
    </div>
  );
};

export default FolderGrid;

// frontend/src/App.tsx
import { useState, useEffect } from 'react';
import { getFolders, Folder } from './api/api';
import { FileGallery } from './components/FileGallery';

function App() {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFolder, setSelectedFolder] = useState<Folder | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const userIdParam = params.get('userId');

    if (userIdParam) {
      const id = parseInt(userIdParam);
      loadFolders(id);
    } else {
      setError('User ID not provided');
      setLoading(false);
    }
  }, []);


  const loadFolders = async (uid: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await getFolders(uid);
      setFolders(data);
    } catch (err) {
      setError('Failed to load folders');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (selectedFolder) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-8">
          <FileGallery
            folderId={selectedFolder.id}
            folderName={selectedFolder.name}
            onBack={() => setSelectedFolder(null)}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-blue-600 text-white py-6 shadow-lg">
        <div className="container mx-auto px-4">
          <h1 className="text-3xl font-bold flex items-center gap-2">
            ☁️ Telegram Cloud Storage
          </h1>
          <p className="text-blue-100 mt-2">Organize your files with unlimited storage</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {loading && (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin text-4xl mb-2">⏳</div>
              <p className="text-gray-600">Loading folders...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-600">{error}</p>
          </div>
        )}

        {!loading && !error && folders.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">No folders yet</p>
            <p className="text-gray-400 mt-2">Create a folder in the bot to get started!</p>
          </div>
        )}

        {!loading && !error && folders.length > 0 && (
          <div>
            <h2 className="text-2xl font-bold mb-6">Your Folders ({folders.length})</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {folders.map((folder) => (
                <button
                  key={folder.id}
                  onClick={() => setSelectedFolder(folder)}
                  className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition text-left"
                >
                  <div className="flex items-start gap-4">
                    <span className="text-4xl">📁</span>
                    <div className="flex-1">
                      <h3 className="font-bold text-lg mb-1">{folder.name}</h3>
                      <p className="text-gray-500 text-sm">
                        {folder.file_count} file{folder.file_count !== 1 ? 's' : ''}
                      </p>
                      <p className="text-gray-400 text-xs mt-1">
                        Created {new Date(folder.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

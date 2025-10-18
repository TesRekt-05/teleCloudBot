// frontend/src/api/api.ts
import axios from 'axios';

const API_BASE_URL = 'https://telegram-cloud-api.onrender.com/api';

// Export interface types
export interface Folder {
  id: number;
  name: string;
  file_count: number;
  created_at: string;
}

export interface File {
  id: number;
  telegram_file_id: string;
  name: string;
  type: string;
  size: number;
  uploaded_at: string;
}

export interface Stats {
  total_folders: number;
  total_files: number;
  total_size_mb: number;
  top_folders_text: string;
}

// API functions
export const getFolders = async (userId: number): Promise<Folder[]> => {
  const response = await axios.get(`${API_BASE_URL}/folders/${userId}`);
  return response.data.folders;
};

export const getFolderFiles = async (folderId: number): Promise<File[]> => {
  const response = await axios.get(`${API_BASE_URL}/folders/${folderId}/files`);
  return response.data.files;
};

// NEW: Get file URL from Telegram
export const getFileUrl = async (fileId: number): Promise<string> => {
  const response = await axios.get(`${API_BASE_URL}/file/${fileId}/url`);
  return response.data.url;
};

export const deleteFile = async (fileId: number): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/files/${fileId}`);
};

export const deleteFolder = async (folderId: number): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/folders/${folderId}`);
};

export const getUserStats = async (userId: number): Promise<Stats> => {
  const response = await axios.get(`${API_BASE_URL}/stats/${userId}`);
  return response.data.stats;
};

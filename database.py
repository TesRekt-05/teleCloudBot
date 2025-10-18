# database.py
from pymongo import MongoClient
from datetime import datetime
import os

class Database:
    def __init__(self, connection_string=None):
        # Store connection string but DON'T connect yet
        self.connection_string = connection_string or os.environ.get('MONGODB_URI')
        self._client = None
        self._db = None
    
    @property
    def client(self):
        """Lazy connection - only connect when actually needed"""
        if self._client is None:
            self._client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                tlsAllowInvalidCertificates=True  # Workaround for SSL issue
            )
        return self._client
    
    @property
    def db(self):
        if self._db is None:
            self._db = self.client['telegram_cloud']
        return self._db
    
    @property
    def users(self):
        return self.db['users']
    
    @property
    def folders(self):
        return self.db['folders']
    
    @property
    def files(self):
        return self.db['files']
    
    def add_user(self, user_id, username, first_name):
        """Add or update user"""
        self.users.update_one(
            {'user_id': user_id},
            {'$set': {
                'username': username,
                'first_name': first_name,
                'created_at': datetime.now()
            }},
            upsert=True
        )
    
    def create_folder(self, user_id, folder_name):
        """Create a new folder"""
        existing = self.folders.find_one({'user_id': user_id, 'folder_name': folder_name})
        if existing:
            return False
        
        self.folders.insert_one({
            'user_id': user_id,
            'folder_name': folder_name,
            'created_at': datetime.now()
        })
        return True
    
    def get_user_folders(self, user_id):
        """Get all folders for a user with file counts"""
        folders = list(self.folders.find({'user_id': user_id}).sort('created_at', -1))
        
        result = []
        for folder in folders:
            file_count = self.files.count_documents({'folder_id': str(folder['_id'])})
            result.append((
                str(folder['_id']),
                folder['folder_name'],
                folder['created_at'].isoformat(),
                file_count
            ))
        
        return result
    
    def add_file(self, folder_id, file_id, file_name, file_type, file_size):
        """Add a file to a folder"""
        self.files.insert_one({
            'folder_id': folder_id,
            'file_id': file_id,
            'file_name': file_name,
            'file_type': file_type,
            'file_size': file_size,
            'uploaded_at': datetime.now()
        })
    
    def get_folder_files(self, folder_id):
        """Get all files in a folder"""
        files = list(self.files.find({'folder_id': folder_id}).sort('uploaded_at', -1))
        
        result = []
        for file in files:
            result.append((
                str(file['_id']),
                file['file_id'],
                file['file_name'],
                file['file_type'],
                file['file_size'],
                file['uploaded_at'].isoformat()
            ))
        
        return result
    
    def delete_file(self, file_db_id):
        """Delete a file"""
        from bson import ObjectId
        self.files.delete_one({'_id': ObjectId(file_db_id)})
    
    def delete_folder(self, folder_id):
        """Delete a folder and all its files"""
        from bson import ObjectId
        self.files.delete_many({'folder_id': folder_id})
        self.folders.delete_one({'_id': ObjectId(folder_id)})
    
    def get_file_info(self, file_db_id):
        """Get file info by ID"""
        from bson import ObjectId
        file = self.files.find_one({'_id': ObjectId(file_db_id)})
        
        if not file:
            return None
        
        return (
            str(file['_id']),
            file['file_id'],
            file['file_name'],
            file['file_type'],
            file['file_size'],
            file['uploaded_at'].isoformat()
        )
    
    def get_user_stats(self, user_id):
        """Get user statistics"""
        total_folders = self.folders.count_documents({'user_id': user_id})
        
        folder_ids = [str(f['_id']) for f in self.folders.find({'user_id': user_id})]
        total_files = self.files.count_documents({'folder_id': {'$in': folder_ids}})
        
        pipeline = [
            {'$match': {'folder_id': {'$in': folder_ids}}},
            {'$group': {'_id': None, 'total_size': {'$sum': '$file_size'}}}
        ]
        result = list(self.files.aggregate(pipeline))
        total_size = result[0]['total_size'] if result else 0
        
        top_folders = []
        for folder_id in folder_ids[:3]:
            from bson import ObjectId
            folder = self.folders.find_one({'_id': ObjectId(folder_id)})
            if folder:
                count = self.files.count_documents({'folder_id': folder_id})
                top_folders.append((folder['folder_name'], count))
        
        top_folders_text = "\n".join([f"📁 {name}: {count} files" for name, count in top_folders]) if top_folders else "No folders yet"
        
        return {
            'total_folders': total_folders,
            'total_files': total_files,
            'total_size_mb': total_size / (1024 * 1024) if total_size else 0,
            'top_folders_text': top_folders_text
        }

# database.py
import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name):
        self.db_name = db_name
        self.create_tables()
    
    def get_connection(self):
        """Create a database connection"""
        return sqlite3.connect(self.db_name)
    
    def create_tables(self):
        """Create the necessary tables if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Enable performance optimizations
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA cache_size = 10000")
        cursor.execute("PRAGMA temp_store = MEMORY")
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TEXT
            )
        ''')
        
        # Folders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                folder_name TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id INTEGER,
                file_id TEXT,
                file_name TEXT,
                file_type TEXT,
                file_size INTEGER,
                uploaded_at TEXT,
                FOREIGN KEY (folder_id) REFERENCES folders (id)
            )
        ''')
        
        # Create indexes for faster searching
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_files_folder 
            ON files(folder_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_files_name 
            ON files(file_name)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_folders_user 
            ON folders(user_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username, first_name):
        """Add a new user to the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def create_folder(self, user_id, folder_name):
        """Create a new folder for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if folder already exists
        cursor.execute('''
            SELECT id FROM folders WHERE user_id = ? AND folder_name = ?
        ''', (user_id, folder_name))
        
        if cursor.fetchone():
            conn.close()
            return False  # Folder already exists
        
        cursor.execute('''
            INSERT INTO folders (user_id, folder_name, created_at)
            VALUES (?, ?, ?)
        ''', (user_id, folder_name, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
    
    def get_user_folders(self, user_id):
        """Get all folders for a user with file counts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.id, f.folder_name, f.created_at, COUNT(fi.id) as file_count
            FROM folders f
            LEFT JOIN files fi ON f.id = fi.folder_id
            WHERE f.user_id = ?
            GROUP BY f.id
            ORDER BY f.created_at DESC
        ''', (user_id,))
        
        folders = cursor.fetchall()
        conn.close()
        return folders
    
    def add_file(self, folder_id, file_id, file_name, file_type, file_size):
        """Add a file to a folder"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO files (folder_id, file_id, file_name, file_type, file_size, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (folder_id, file_id, file_name, file_type, file_size, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_folder_files(self, folder_id):
        """Get all files in a folder"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, file_id, file_name, file_type, file_size, uploaded_at
            FROM files
            WHERE folder_id = ?
            ORDER BY uploaded_at DESC
        ''', (folder_id,))
        
        files = cursor.fetchall()
        conn.close()
        return files
    
    def delete_file(self, file_db_id):
        """Delete a file from the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM files WHERE id = ?
        ''', (file_db_id,))
        
        conn.commit()
        conn.close()
    
    def delete_folder(self, folder_id):
        """Delete a folder and all its files"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Delete all files in the folder first
        cursor.execute('''
            DELETE FROM files WHERE folder_id = ?
        ''', (folder_id,))
        
        # Delete the folder
        cursor.execute('''
            DELETE FROM folders WHERE id = ?
        ''', (folder_id,))
        
        conn.commit()
        conn.close()
    
    def get_file_info(self, file_db_id):
        """Get file information by database ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT file_name, file_type, file_size FROM files WHERE id = ?
        ''', (file_db_id,))
        
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_user_stats(self, user_id):
        """Get statistics for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get total folders
        cursor.execute('''
            SELECT COUNT(*) FROM folders WHERE user_id = ?
        ''', (user_id,))
        total_folders = cursor.fetchone()[0]
        
        # Get total files and size
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(fi.file_size), 0)
            FROM folders f
            LEFT JOIN files fi ON f.id = fi.folder_id
            WHERE f.user_id = ?
        ''', (user_id,))
        total_files, total_size = cursor.fetchone()
        
        # Get top 3 largest folders
        cursor.execute('''
            SELECT f.folder_name, COUNT(fi.id) as file_count
            FROM folders f
            LEFT JOIN files fi ON f.id = fi.folder_id
            WHERE f.user_id = ?
            GROUP BY f.id
            ORDER BY file_count DESC
            LIMIT 3
        ''', (user_id,))
        top_folders = cursor.fetchall()
        
        conn.close()
        
        # Format top folders text
        if top_folders:
            top_folders_text = "\n".join([f"📁 {name}: {count} files" for name, count in top_folders])
        else:
            top_folders_text = "No folders yet"
        
        return {
            'total_folders': total_folders,
            'total_files': total_files,
            'total_size_mb': total_size / (1024 * 1024) if total_size else 0,
            'top_folders_text': top_folders_text
        }

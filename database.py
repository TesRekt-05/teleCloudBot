# database.py
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

class Database:
    def __init__(self, db_url=None):
        # Use PostgreSQL URL from environment or parameter
        self.db_url = db_url or os.environ.get('DATABASE_URL')
        self.create_tables()
    
    def get_connection(self):
        """Create a database connection"""
        return psycopg2.connect(self.db_url)
    
    def create_tables(self):
        """Create the necessary tables if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Folders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                folder_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id SERIAL PRIMARY KEY,
                folder_id INTEGER REFERENCES folders(id),
                file_id TEXT,
                file_name TEXT,
                file_type TEXT,
                file_size BIGINT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_files_folder ON files(folder_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_folders_user ON folders(user_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username, first_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
        ''', (user_id, username, first_name))
        conn.commit()
        conn.close()
    
    def create_folder(self, user_id, folder_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute('''
            SELECT id FROM folders WHERE user_id = %s AND folder_name = %s
        ''', (user_id, folder_name))
        
        if cursor.fetchone():
            conn.close()
            return False
        
        cursor.execute('''
            INSERT INTO folders (user_id, folder_name)
            VALUES (%s, %s)
        ''', (user_id, folder_name))
        conn.commit()
        conn.close()
        return True
    
    def get_user_folders(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT f.id, f.folder_name, f.created_at, COUNT(fi.id) as file_count
            FROM folders f
            LEFT JOIN files fi ON f.id = fi.folder_id
            WHERE f.user_id = %s
            GROUP BY f.id
            ORDER BY f.created_at DESC
        ''', (user_id,))
        folders = cursor.fetchall()
        conn.close()
        return folders
    
    def add_file(self, folder_id, file_id, file_name, file_type, file_size):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO files (folder_id, file_id, file_name, file_type, file_size)
            VALUES (%s, %s, %s, %s, %s)
        ''', (folder_id, file_id, file_name, file_type, file_size))
        conn.commit()
        conn.close()
    
    def get_folder_files(self, folder_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, file_id, file_name, file_type, file_size, uploaded_at
            FROM files
            WHERE folder_id = %s
            ORDER BY uploaded_at DESC
        ''', (folder_id,))
        files = cursor.fetchall()
        conn.close()
        return files
    
    def delete_file(self, file_db_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM files WHERE id = %s', (file_db_id,))
        conn.commit()
        conn.close()
    
    def delete_folder(self, folder_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM files WHERE folder_id = %s', (folder_id,))
        cursor.execute('DELETE FROM folders WHERE id = %s', (folder_id,))
        conn.commit()
        conn.close()
    
    def get_file_info(self, file_db_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, file_id, file_name, file_type, file_size, uploaded_at
            FROM files WHERE id = %s
        ''', (file_db_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_user_stats(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM folders WHERE user_id = %s', (user_id,))
        total_folders = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(fi.file_size), 0)
            FROM folders f
            LEFT JOIN files fi ON f.id = fi.folder_id
            WHERE f.user_id = %s
        ''', (user_id,))
        total_files, total_size = cursor.fetchone()
        
        cursor.execute('''
            SELECT f.folder_name, COUNT(fi.id) as file_count
            FROM folders f
            LEFT JOIN files fi ON f.id = fi.folder_id
            WHERE f.user_id = %s
            GROUP BY f.id, f.folder_name
            ORDER BY file_count DESC
            LIMIT 3
        ''', (user_id,))
        top_folders = cursor.fetchall()
        
        conn.close()
        
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

# app.py
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from database import Database
from config import DATABASE_NAME, BOT_TOKEN
import os

app = Flask(__name__, static_folder='frontend/dist')
CORS(app)

# Initialize database
db = Database(DATABASE_NAME)

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'API is running'})

# Get user folders
@app.route('/api/folders/<int:user_id>', methods=['GET'])
def get_folders(user_id):
    folders = db.get_user_folders(user_id)
    folders_list = [{
        'id': folder[0],
        'name': folder[1],
        'created_at': folder[2],
        'file_count': folder[3]
    } for folder in folders]
    return jsonify({'success': True, 'folders': folders_list})

# Get files in a folder
@app.route('/api/folders/<int:folder_id>/files', methods=['GET'])
def get_files(folder_id):
    files = db.get_folder_files(folder_id)
    files_list = [{
        'id': file[0],
        'telegram_file_id': file[1],
        'name': file[2],
        'type': file[3],
        'size': file[4],
        'uploaded_at': file[5]
    } for file in files]
    return jsonify({'success': True, 'files': files_list})

# NEW: Get Telegram file URL
@app.route('/api/file/<file_id>/url', methods=['GET'])
def get_file_url(file_id):
    """Get direct URL to download file from Telegram"""
    try:
        # Get file info from database
        file_info = db.get_file_info(int(file_id))
        if not file_info:
            return jsonify({'success': False, 'message': 'File not found'}), 404
        
        telegram_file_id = file_info[1]  # Get telegram_file_id from database
        
        # Construct Telegram Bot API file URL
        file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={telegram_file_id}"
        
        import requests
        response = requests.get(file_url)
        data = response.json()
        
        if data.get('ok'):
            file_path = data['result']['file_path']
            download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            return jsonify({
                'success': True,
                'url': download_url,
                'file_path': file_path
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to get file from Telegram'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Delete file
@app.route('/api/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    db.delete_file(file_id)
    return jsonify({'success': True, 'message': 'File deleted'})

# Delete folder
@app.route('/api/folders/<int:folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    db.delete_folder(folder_id)
    return jsonify({'success': True, 'message': 'Folder deleted'})

# Get user stats
@app.route('/api/stats/<int:user_id>', methods=['GET'])
def get_stats(user_id):
    stats = db.get_user_stats(user_id)
    return jsonify({'success': True, 'stats': stats})

# Serve React app
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    
    print("🚀 Flask API Server Starting...")
    print("📊 API Endpoints:")
    print("   - GET  /api/health")
    print("   - GET  /api/folders/<user_id>")
    print("   - GET  /api/folders/<folder_id>/files")
    print("   - GET  /api/file/<file_id>/url")  # NEW!
    print("   - DELETE /api/files/<file_id>")
    print("   - DELETE /api/folders/<folder_id>")
    print("   - GET  /api/stats/<user_id>")
    print(f"\n🌐 Server running on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)

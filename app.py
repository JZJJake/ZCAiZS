import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from knowledge_base import KnowledgeBase
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-key-for-dev")

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Global state
kb = KnowledgeBase()
client_access_enabled = True

@app.route('/')
def index():
    """Client web page."""
    return render_template('index.html', enabled=client_access_enabled)

@app.route('/admin')
def admin():
    """Admin web page."""
    stats = kb.get_stats()
    return render_template('admin.html', stats=stats, enabled=client_access_enabled)

# --- Client APIs ---

@app.route('/api/query', methods=['POST'])
def api_query():
    """Client endpoint to query the Knowledge Base."""
    if not client_access_enabled:
        return jsonify({"error": "目前系统正在维护或暂未开放，请稍后再试。"}), 403

    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "缺少查询内容"}), 400

    user_query = data['query']
    answer = kb.query(user_query)

    return jsonify({"answer": answer})

# --- Admin APIs ---

@app.route('/api/admin/toggle', methods=['POST'])
def api_toggle_client():
    """Toggle client access."""
    global client_access_enabled
    data = request.json
    if data and 'enabled' in data:
        client_access_enabled = bool(data['enabled'])
    return jsonify({"success": True, "enabled": client_access_enabled})

@app.route('/api/admin/upload', methods=['POST'])
def api_upload_md():
    """Upload a markdown file and process it into the database."""
    if 'file' not in request.files:
        flash('没有找到文件')
        return redirect(url_for('admin'))

    file = request.files['file']
    if file.filename == '':
        flash('未选择文件')
        return redirect(url_for('admin'))

    if file and file.filename.endswith('.md'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Process into KnowledgeBase
        try:
            count = kb.process_file(filepath)
            flash(f'成功处理文件 {filename}，共导入 {count} 条问答记录。')
        except Exception as e:
            flash(f'处理文件时发生错误: {e}')

        return redirect(url_for('admin'))
    else:
        flash('只支持 .md 文件')
        return redirect(url_for('admin'))

@app.route('/api/admin/clear', methods=['POST'])
def api_clear_db():
    """Clear all data from the databases."""
    try:
        kb.clear_database()
        return jsonify({"success": True, "message": "数据库已清空"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/admin/graph_data', methods=['GET'])
def api_graph_data():
    """Get nodes and edges for the network graph."""
    try:
        data = kb.get_graph_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run the server
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

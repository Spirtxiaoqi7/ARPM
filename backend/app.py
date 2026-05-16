"""
ARPM-v4 主入口
"""
import os
import sys
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory, render_template
from config import FlaskConfig, ensure_directories
from utils import admin_logger
from utils.app_logger import get_app_logger

# 确保目录存在
ensure_directories()
app_logger = get_app_logger()

# 创建Flask应用
app = Flask(
    __name__,
    template_folder='web/templates',
    static_folder='web/static'
)
app.secret_key = FlaskConfig.SECRET_KEY

# 禁用开发服务器警告
from flask.cli import show_server_banner
show_server_banner = lambda *args, **kwargs: None
logging.getLogger('werkzeug').disabled = True

# 注册蓝图
from api.chat import chat_bp
from api.knowledge import knowledge_bp
from api.session import session_bp
from api.diagnose import diagnose_bp
app.register_blueprint(chat_bp)
app.register_blueprint(knowledge_bp)
app.register_blueprint(session_bp)
app.register_blueprint(diagnose_bp)

# 前端路由
@app.route('/')
def index():
    return render_template('index.html')

# 错误处理
@app.errorhandler(404)
def not_found(e):
    return {'error': '接口不存在'}, 404

@app.errorhandler(500)
def internal_error(e):
    return {'error': '服务器内部错误'}, 500

if __name__ == '__main__':
    port = FlaskConfig.PORT
    debug = FlaskConfig.DEBUG
    app_logger.info("service starting port=%s debug=%s", port, debug)
    app_logger.info(
        "admin logger loaded schema_version=%s module_path=%s",
        admin_logger.SCHEMA_VERSION,
        admin_logger.__file__,
    )
    
    print("=" * 60)
    print(f"  ARPM v4.0 智能对话系统")
    print("=" * 60)
    print(f"  访问地址: http://localhost:{port}")
    print(f"  调试模式: {'开启' if debug else '关闭'}")
    print("=" * 60)
    print("  按 Ctrl+C 停止服务")
    print("")
    
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)

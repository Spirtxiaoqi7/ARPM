"""
诊断 API 路由
"""
from flask import Blueprint, request, jsonify

from core.diagnostician import diagnostician

diagnose_bp = Blueprint('diagnose', __name__)


@diagnose_bp.route('/api/diagnostics', methods=['GET', 'POST'])
def run_diagnostics():
    """运行系统诊断"""
    auto_fix = False
    if request.method == 'POST':
        data = request.get_json() or {}
        auto_fix = data.get('auto_fix', False)
    
    try:
        report = diagnostician.run_all_checks(auto_fix=auto_fix)
        return jsonify(report.dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@diagnose_bp.route('/api/diagnostics/arpm', methods=['GET'])
def get_arpm_report():
    """获取ARPM组件完整报告（含遗忘逻辑文档）"""
    try:
        report = diagnostician.generate_arpm_report()
        return jsonify(report.dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

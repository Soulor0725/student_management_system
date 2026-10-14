"""混沌测试控制接口（/chaos/*）。

安全约束：这些端点能把整个应用切换到随机故障模式，因此只接受
本机（loopback）来源，或携带 `X-Chaos-Token: <CHAOS_API_TOKEN>`
的远程调用（run_chaos_test.py 等测试执行器可用环境变量下发 token）。
"""

import hmac
import os
from ipaddress import ip_address

from flask import Blueprint, jsonify, request
from .chaos_injector import ChaosController

chaos_bp = Blueprint('chaos', __name__)
chaos_controller = ChaosController()


def _is_loopback() -> bool:
    try:
        return ip_address(request.remote_addr or '').is_loopback
    except ValueError:
        return False


def _token_ok() -> bool:
    token = os.environ.get('CHAOS_API_TOKEN')
    if not token:
        return False
    return hmac.compare_digest(str(request.headers.get('X-Chaos-Token', '')), token)


@chaos_bp.before_request
def restrict_chaos_access():
    """混沌控制接口仅允许本机调用；远程需携带 X-Chaos-Token。"""
    if _is_loopback() or _token_ok():
        return None
    return jsonify({
        'status': 'error',
        'message': 'chaos endpoints are local-only (loopback or X-Chaos-Token required)'
    }), 403


@chaos_bp.route('/chaos/status', methods=['GET'])
def get_chaos_status():
    """获取混沌测试状态"""
    return jsonify(chaos_controller.status())

@chaos_bp.route('/chaos/start', methods=['POST'])
def start_chaos():
    """启动混沌测试"""
    data = request.get_json() or {}
    probability = data.get('probability', 0.1)
    chaos_controller.start(probability)
    return jsonify({
        'status': 'success',
        'message': f'混沌测试已启动，故障概率: {probability*100}%'
    })

@chaos_bp.route('/chaos/stop', methods=['POST'])
def stop_chaos():
    """停止混沌测试"""
    chaos_controller.stop()
    return jsonify({
        'status': 'success',
        'message': '混沌测试已停止'
    })

@chaos_bp.route('/chaos/toggle', methods=['POST'])
def toggle_chaos():
    """切换混沌测试状态"""
    if chaos_controller.enabled:
        chaos_controller.stop()
        return jsonify({
            'status': 'success',
            'message': '混沌测试已停止'
        })
    else:
        chaos_controller.start()
        return jsonify({
            'status': 'success',
            'message': '混沌测试已启动'
        })

@chaos_bp.route('/chaos/simulate/db-failure', methods=['POST'])
def simulate_db_failure():
    """模拟数据库故障"""
    data = request.get_json() or {}
    duration = data.get('duration', 30)
    chaos_controller.simulate_db_failure(duration)
    return jsonify({
        'status': 'success',
        'message': f'数据库故障模拟已启动，持续 {duration} 秒'
    })

@chaos_bp.route('/chaos/config', methods=['PUT'])
def update_chaos_config():
    """更新混沌测试配置"""
    data = request.get_json() or {}
    if 'probability' in data:
        chaos_controller.probability = data['probability']
    return jsonify({
        'status': 'success',
        'message': '混沌测试配置已更新',
        'config': chaos_controller.status()
    })

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import os
import sys
from typing import List, Dict, Optional
from datetime import datetime
import logging

# 导入自定义模块
from device_manager import DeviceManager
from scanner_service import ScannerService
from calibration_service import CalibrationService

# 获取前端目录的绝对路径，支持PyInstaller打包
if getattr(sys, 'frozen', False):
    # PyInstaller打包环境
    base_dir = sys._MEIPASS
    frontend_dir = os.path.join(base_dir, 'frontend')
    backend_dir = os.path.join(base_dir, 'backend')
else:
    # 开发环境
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir)
    frontend_dir = os.path.join(base_dir, 'frontend')
    backend_dir = current_dir

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用，指定静态文件目录和URL路径
app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
app.config['SECRET_KEY'] = 'esp-hi-secret-key-2025'
CORS(app)  # 允许跨域请求

# 明确使用threading异步模式，确保打包后能正常运行
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
logger.info("SocketIO initialized with threading async mode")

# 全局服务实例
scanner_service = ScannerService()
device_manager = DeviceManager()
calibration_service = CalibrationService()

# ==================== 设备扫描相关 API ====================

@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    """开始扫描局域网内的ESP-HI设备"""
    try:
        logger.info("开始扫描设备...")
        devices = scanner_service.scan_devices()
        
        # 保存扫描结果
        scanner_service.save_devices(devices)
        
        # 通过WebSocket推送扫描结果
        socketio.emit('scan_complete', {
            'devices': devices,
            'count': len(devices),
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'devices': devices,
            'count': len(devices)
        })
    except Exception as e:
        logger.error(f"扫描失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """获取已保存的设备列表，并包含当前连接状态"""
    try:
        devices = scanner_service.load_devices()
        
        # 获取当前已连接的设备 (从内存中)
        connected_devices = list(device_manager.controllers.keys())
        
        # 获取当前校准状态
        calibration_device = calibration_service.current_device
        
        return jsonify({
            'success': True,
            'devices': devices,
            'connected_devices': connected_devices,
            'calibration_device': calibration_device,
            'count': len(devices)
        })
    except Exception as e:
        logger.error(f"获取设备列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/devices/delete', methods=['POST'])
def delete_device():
    """删除指定设备"""
    try:
        data = request.json
        ip = data.get('ip')
        if not ip:
            return jsonify({'success': False, 'error': 'IP address required'}), 400
        
        success = scanner_service.remove_device(ip)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"删除设备失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/devices/select', methods=['POST'])
def select_devices():
    """选择要控制的设备"""
    try:
        data = request.get_json()
        device_ips = data.get('devices', [])
        
        if not device_ips:
            return jsonify({
                'success': False,
                'error': '请至少选择一个设备'
            }), 400
        
        # 初始化设备管理器
        # device_manager.initialize_devices 返回 {'active_devices': [...], 'failed_devices': [...]}
        results = device_manager.initialize_devices(device_ips)
        
        success_ips = results.get('active_devices', [])
        failed_ips = results.get('failed_devices', [])
        
        return jsonify({
            'success': True,
            'selected_count': len(success_ips),
            'success_devices': success_ips,
            'failed_devices': failed_ips
        })
    except Exception as e:
        logger.error(f"选择设备失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/devices/disconnect', methods=['POST'])
def disconnect_device():
    """断开设备连接"""
    try:
        data = request.get_json()
        ip = data.get('ip')
        
        if not ip:
            return jsonify({
                'success': False,
                'error': '请指定要断开的设备'
            }), 400
        
        # 从 device_manager 中移除设备
        if ip in device_manager.controllers:
            del device_manager.controllers[ip]
            logger.info(f"已断开设备连接: {ip}")
            return jsonify({
                'success': True,
                'message': f'已断开设备 {ip} 的连接'
            })
        else:
            return jsonify({
                'success': False,
                'error': '该设备未连接'
            }), 400
    except Exception as e:
        logger.error(f"断开设备失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 设备控制相关 API ====================

@app.route('/api/control/action', methods=['POST'])
def execute_action():
    """执行预设动作"""
    try:
        if calibration_service.current_device:
            return jsonify({
                'success': False,
                'error': '舵机校准模式下无法执行此操作，请先退出舵机校准模式'
            }), 400

        if not device_manager.controllers:
            return jsonify({
                'success': False,
                'error': '没有已连接的设备，请先连接设备'
            }), 400

        data = request.get_json()
        action_id = data.get('action_id')
        
        if not action_id:
            return jsonify({
                'success': False,
                'error': '缺少动作ID'
            }), 400
        
        results = device_manager.execute_action(action_id)
        
        # 通过WebSocket推送执行结果
        socketio.emit('action_executed', {
            'action_id': action_id,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        logger.error(f"执行动作失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/control/move', methods=['POST'])
def execute_move():
    """执行移动控制"""
    try:
        if calibration_service.current_device:
            return jsonify({
                'success': False,
                'error': '舵机校准模式下无法执行此操作，请先退出舵机校准模式'
            }), 400

        if not device_manager.controllers:
            return jsonify({
                'success': False,
                'error': '没有已连接的设备，请先连接设备'
            }), 400

        data = request.get_json()
        direction = data.get('direction')
        
        if not direction:
            return jsonify({
                'success': False,
                'error': '缺少移动方向'
            }), 400
        
        results = device_manager.execute_move(direction)
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        logger.error(f"执行移动失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/control/continuous/start', methods=['POST'])
def start_continuous_move():
    """开始连续移动"""
    try:
        if calibration_service.current_device:
            return jsonify({
                'success': False,
                'error': '舵机校准模式下无法执行此操作，请先退出舵机校准模式'
            }), 400

        if not device_manager.controllers:
            return jsonify({
                'success': False,
                'error': '没有已连接的设备，请先连接设备'
            }), 400

        data = request.get_json()
        direction = data.get('direction')
        delay = data.get('delay', None)
        
        if not direction:
            return jsonify({
                'success': False,
                'error': '缺少移动方向'
            }), 400
        
        results = device_manager.start_continuous_move(direction, delay)
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        logger.error(f"开始连续移动失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/control/continuous/stop', methods=['POST'])
def stop_continuous_move():
    """停止连续移动"""
    try:
        results = device_manager.stop_continuous_move()
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        logger.error(f"停止连续移动失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/control/sequence', methods=['POST'])
def execute_sequence():
    """执行自定义动作序列"""
    if calibration_service.current_device:
        return jsonify({
            'success': False,
            'error': '舵机校准模式下无法执行此操作，请先退出舵机校准模式'
        }), 400

    if not device_manager.controllers:
        return jsonify({
            'success': False,
            'error': '没有已连接的设备，请先连接设备'
        }), 400

    data = request.json
    sequence = data.get('sequence', [])
    
    def run_sequence():
        socketio.emit('sequence_status', {'status': 'started', 'message': '序列开始执行'})
        try:
            device_manager.execute_sequence(sequence)
            socketio.emit('sequence_status', {'status': 'completed', 'message': '序列执行完成'})
        except Exception as e:
            socketio.emit('sequence_status', {'status': 'error', 'message': f'序列执行出错: {str(e)}'})

    # 在后台线程运行序列，避免阻塞主线程
    socketio.start_background_task(run_sequence)
    
    return jsonify({'success': True, 'message': 'Sequence started'})

# ==================== 校准相关 API ====================

@app.route('/api/calibration/start', methods=['POST'])
def start_calibration():
    """进入校准模式"""
    try:
        data = request.get_json()
        device_ip = data.get('device')
        
        if not device_ip:
            return jsonify({
                'success': False,
                'error': '请选择要校准的设备'
            }), 400
        
        result = calibration_service.start_calibration(device_ip)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"进入校准模式失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/calibration/exit', methods=['POST'])
def exit_calibration():
    """退出舵机校准模式"""
    try:
        data = request.get_json() or {}
        force = data.get('force', False)
        
        result = calibration_service.exit_calibration(force=force)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"退出校准模式失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/calibration/adjust', methods=['POST'])
def adjust_servo():
    """调整舵机角度"""
    try:
        data = request.get_json()
        servo = data.get('servo')
        value = data.get('value')
        
        if not servo or value is None:
            return jsonify({
                'success': False,
                'error': '缺少舵机编号或角度值'
            }), 400
        
        result = calibration_service.adjust_servo(servo, value)
        
        # 实时推送调整结果
        socketio.emit('servo_adjusted', {
            'servo': servo,
            'value': value,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"调整舵机失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== WebSocket 事件处理 ====================

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info('客户端已连接')
    emit('connected', {'message': '已连接到服务器'})

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    logger.info('客户端已断开连接')

@socketio.on('ping')
def handle_ping():
    """心跳检测"""
    emit('pong', {'timestamp': datetime.now().isoformat()})

# ==================== 健康检查 ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_devices': len(device_manager.controllers),
        'version': '1.0.0'
    })

# ==================== 静态文件服务 ====================

@app.route('/')
def index():
    """主页"""
    return app.send_static_file('index.html')

if __name__ == '__main__':
    logger.info("ESP-HI 控制服务器启动中...")
    logger.info("访问 http://localhost:5000 以使用Web界面")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

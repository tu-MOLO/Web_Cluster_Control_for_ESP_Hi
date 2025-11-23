import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# 控制配置
MAX_CONCURRENT_THREADS = 20
CONTINUOUS_MOVE_INTERVAL = 500

ACTION_NAMES = {
    '1': '趴下', '2': '鞠躬', '3': '后仰', '4': '摇摆',
    '5': '前后', '6': '左右', '7': '握手', '8': '戳戳',
    '9': '抖腿', '10': '前跳', '11': '后跳', '12': '收腿',
    'F': '前进', 'B': '后退', 'L': '左转', 'R': '右转'
}

CURL_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,zh-HK;q=0.8",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Origin": "http://esp-hi.local",
    "Referer": "http://esp-hi.local/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

class ServoDogController:
    """单个舵机狗设备控制器"""
    
    def __init__(self, device: str, port=80):
        self.device = device
        self.control_url = f"http://{device}:{port}/control"
        self.headers = CURL_HEADERS.copy()
        self.headers["Host"] = device
        self.continuous_timer = None
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False

    def _send_raw_command(self, data: str) -> Dict:
        """发送原始命令到设备"""
        try:
            response = self.session.post(
                url=self.control_url,
                data=data,
                timeout=0.5,
                allow_redirects=False
            )
            response.raise_for_status()
            return {"success": True, "response": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_action(self, action_id: str) -> Dict:
        """执行预置动作"""
        if action_id not in ACTION_NAMES:
            return {"success": False, "error": "无效的动作ID"}
        
        result = self._send_raw_command(f'{{"action":"{action_id}"}}')
        return {
            "success": result["success"] and result.get("response") == '{"code":200}',
            "message": "成功" if result["success"] else f"失败：{result.get('error', result.get('response'))}"
        }

    def execute_move(self, direction: str) -> Dict:
        """执行单次移动"""
        direction = direction.upper()
        if direction not in ['F', 'B', 'L', 'R']:
            return {"success": False, "error": "无效的移动方向"}
        
        result = self._send_raw_command(f'{{"move":"{direction}"}}')
        return {
            "success": result["success"] and result.get("response") == '{"code":200}',
            "message": "成功" if result["success"] else f"失败：{result.get('error', result.get('response'))}"
        }

    def start_continuous_move(self, direction: str, delay: float = None) -> Dict:
        """开始连续移动"""
        direction = direction.upper()
        if direction not in ['F', 'B', 'L', 'R']:
            return {"success": False, "error": "无效的移动方向"}
        
        move_interval = delay * 1000 if delay is not None else CONTINUOUS_MOVE_INTERVAL
        if move_interval <= 0:
            return {"success": False, "error": "延迟时间必须大于0"}
        
        self.stop_continuous_move()
        
        def _send_continuous():
            next_send_time = time.time()
            while self.continuous_timer and self.continuous_timer.running:
                self._send_raw_command(f'{{"move":"{direction}"}}')
                next_send_time += move_interval / 1000
                current_time = time.time()
                if next_send_time > current_time:
                    time.sleep(next_send_time - current_time)
        
        self.continuous_timer = _ContinuousTimer(_send_continuous)
        self.continuous_timer.start()
        
        return {
            "success": True,
            "message": f"已启动连续移动（延迟：{move_interval:.1f}ms）"
        }

    def stop_continuous_move(self) -> Dict:
        """停止连续移动"""
        if self.continuous_timer:
            self.continuous_timer.stop()
            self.continuous_timer = None
            return {"success": True, "message": "已停止连续移动"}
        return {"success": True, "message": "无连续移动"}

    def run_sequence(self, sequence: List[Dict]) -> Dict:
        """运行动作序列"""
        try:
            for item in sequence:
                if "action" in item:
                    cmd = f'{{"action":"{item["action"]}"}}'
                elif "move" in item:
                    cmd = f'{{"move":"{item["move"].upper()}"}}'
                else:
                    return {"success": False, "error": "序列项格式错误"}
                
                self._send_raw_command(cmd)
                time.sleep(item.get("delay", 1.0))
            
            return {"success": True, "message": "序列执行完成"}
        except Exception as e:
            return {"success": False, "error": f"序列执行失败：{str(e)}"}


class _ContinuousTimer:
    """连续移动定时器"""
    
    def __init__(self, func):
        self.func = func
        self.running = False
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        while self.running:
            try:
                self.func()
            except Exception as e:
                logger.warning(f"连续移动出错：{str(e)}")
                if self.running:
                    time.sleep(0.1)

    def start(self):
        self.running = True
        if not self.thread.is_alive():
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)


class DeviceManager:
    """多设备管理器"""
    
    def __init__(self):
        self.controllers = {}
        self.executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_THREADS)

    def initialize_devices(self, devices: List[str]) -> Dict:
        """初始化设备控制器"""
        # 清空旧的控制器，确保只控制当前选中的设备
        self.controllers.clear()
        
        futures = []
        for device in devices:
            futures.append(self.executor.submit(self._verify_device, device))
        
        active_devices = []
        failed_devices = []
        
        for future in as_completed(futures):
            device, controller, success = future.result()
            if success:
                self.controllers[device] = controller
                active_devices.append(device)
                logger.info(f"设备 {device} 连接成功")
            else:
                failed_devices.append(device)
                logger.warning(f"设备 {device} 连接失败")
        
        return {
            "active_devices": active_devices,
            "failed_devices": failed_devices
        }

    def _verify_device(self, device: str) -> tuple:
        """验证设备连接"""
        try:
            controller = ServoDogController(device)
            result = controller._send_raw_command('{}')
            return (device, controller, result["success"] and result["response"] == '{"code":200}')
        except:
            return (device, None, False)

    def execute_action(self, action_id: str) -> Dict:
        """批量执行动作"""
        if not self.controllers:
            return {"error": "没有可用设备"}
        
        results = {}
        futures = []
        
        for device, controller in self.controllers.items():
            futures.append(
                self.executor.submit(
                    lambda d, c: (d, c.execute_action(action_id)),
                    device, controller
                )
            )
        
        for future in as_completed(futures):
            device, result = future.result()
            results[device] = result
        
        return results

    def execute_move(self, direction: str) -> Dict:
        """批量执行移动"""
        if not self.controllers:
            return {"error": "没有可用设备"}
        
        results = {}
        futures = []
        
        for device, controller in self.controllers.items():
            futures.append(
                self.executor.submit(
                    lambda d, c, dir: (d, c.execute_move(dir)),
                    device, controller, direction
                )
            )
        
        for future in as_completed(futures):
            device, result = future.result()
            results[device] = result
        
        return results

    def start_continuous_move(self, direction: str, delay: float = None) -> Dict:
        """批量开始连续移动"""
        if not self.controllers:
            return {"error": "没有可用设备"}
        
        results = {}
        futures = []
        
        for device, controller in self.controllers.items():
            futures.append(
                self.executor.submit(
                    lambda d, c, dir, del_val: (d, c.start_continuous_move(dir, del_val)),
                    device, controller, direction, delay
                )
            )
        
        for future in as_completed(futures):
            device, result = future.result()
            results[device] = result
        
        return results

    def stop_continuous_move(self) -> Dict:
        """批量停止连续移动"""
        if not self.controllers:
            return {"error": "没有可用设备"}
        
        results = {}
        futures = []
        
        for device, controller in self.controllers.items():
            futures.append(
                self.executor.submit(
                    lambda d, c: (d, c.stop_continuous_move()),
                    device, controller
                )
            )
        
        for future in as_completed(futures):
            device, result = future.result()
            results[device] = result
        
        return results

    def execute_sequence(self, sequence: List[Dict]) -> Dict:
        """批量执行序列"""
        if not self.controllers:
            return {"error": "没有可用设备"}
        
        results = {}
        futures = []
        
        for device, controller in self.controllers.items():
            futures.append(
                self.executor.submit(
                    lambda d, c, seq: (d, c.run_sequence(seq)),
                    device, controller, sequence
                )
            )
        
        for future in as_completed(futures):
            device, result = future.result()
            results[device] = result
        
        return results

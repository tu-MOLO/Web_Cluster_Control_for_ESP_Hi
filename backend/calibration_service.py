import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# 超时时间
HTTP_TIMEOUT = 3.0

# 四肢编号映射
SERVO_MAP = {
    "1": "fl",  # 前左腿
    "2": "fr",  # 前右腿
    "3": "bl",  # 后左腿
    "4": "br"   # 后右腿
}

SERVO_NAME = {
    "fl": "前左腿",
    "fr": "前右腿",
    "bl": "后左腿",
    "br": "后右腿"
}


class CalibrationService:
    """舵机校准服务"""
    
    def __init__(self):
        self.current_device = None
        self.session = None

    def _init_session(self, device: str):
        """初始化会话"""
        if self.current_device != device or self.session is None:
            self.current_device = device
            self.session = requests.Session()
            self.session.headers.update({
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,zh-HK;q=0.8",
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "Referer": f"http://{device}/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            self.session.verify = False

    def _send_request(self, endpoint: str, data: Optional[Dict] = None, method: str = "POST") -> Dict:
        """发送请求到设备"""
        try:
            if not self.current_device or not self.session:
                return {"success": False, "error": "未初始化设备"}
            
            url = f"http://{self.current_device}/{endpoint}"
            
            if method.upper() == "GET":
                response = self.session.get(url, timeout=HTTP_TIMEOUT)
            else:  # POST
                response = self.session.post(url, json=data, timeout=HTTP_TIMEOUT)
            
            response.raise_for_status()
            return {"success": True, "response": response.text}
        except Exception as e:
            logger.error(f"请求失败 [{endpoint}]: {str(e)}")
            return {"success": False, "error": str(e)}

    def start_calibration(self, device: str) -> Dict:
        """进入校准模式"""
        try:
            self._init_session(device)
            logger.info(f"向设备 {device} 发送进入校准模式指令...")
            
            result = self._send_request("start_calibration", method="GET")
            
            if result["success"]:
                logger.info("已进入校准模式")
                return {
                    "success": True,
                    "message": "已进入校准模式",
                    "device": device
                }
            else:
                return {
                    "success": False,
                    "error": f"进入校准模式失败：{result['error']}"
                }
        except Exception as e:
            logger.error(f"进入校准模式失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def exit_calibration(self, force: bool = False) -> Dict:
        """退出校准模式"""
        try:
            if not self.current_device:
                return {"success": False, "error": "没有活动的校准会话"}
            
            device = self.current_device
            error_msg = None
            
            # 尝试发送退出命令
            try:
                logger.info(f"向设备 {device} 发送退出校准模式指令...")
                result = self._send_request("exit_calibration", method="GET")
                if not result["success"]:
                    error_msg = f"退出校准模式失败：{result['error']}"
            except Exception as e:
                error_msg = str(e)
            
            # 如果请求失败且不是强制退出，则返回错误
            if error_msg and not force:
                return {
                    "success": False,
                    "error": error_msg
                }
            
            # 如果成功或强制退出，清理状态
            self.current_device = None
            self.session = None
            
            if force and error_msg:
                logger.warning(f"已强制退出校准模式（设备通信失败: {error_msg}）")
                return {
                    "success": True,
                    "message": "已强制退出校准模式",
                    "device": device,
                    "warning": error_msg
                }
            
            logger.info("已退出校准模式，校准结果已保存")
            return {
                "success": True,
                "message": "已退出校准模式，校准结果已保存",
                "device": device
            }
        except Exception as e:
            logger.error(f"退出校准模式异常: {str(e)}")
            # 即使发生未预期的异常，如果是强制退出，也要清理
            if force:
                self.current_device = None
                self.session = None
                return {"success": True, "message": "已强制退出校准模式（异常恢复）"}
            return {"success": False, "error": str(e)}

    def adjust_servo(self, servo: str, value: int) -> Dict:
        """调整舵机角度"""
        try:
            if not self.current_device:
                return {"success": False, "error": "没有活动的校准会话"}
            
            # 验证角度范围
            if not (-25 <= value <= 25):
                return {"success": False, "error": "角度必须在 -25 ~ 25 之间"}
            
            # 将数字编号转换为舵机代码
            servo_code = SERVO_MAP.get(servo, servo)
            servo_name = SERVO_NAME.get(servo_code, "未知")
            
            logger.info(f"调整 {servo_name} 角度至 {value}...")
            result = self._send_request("adjust", {"servo": servo_code, "value": value}, method="POST")
            
            if result["success"]:
                logger.info(f"{servo_name} 角度调整成功")
                return {
                    "success": True,
                    "message": f"{servo_name} 角度调整成功",
                    "servo": servo_code,
                    "value": value
                }
            else:
                return {
                    "success": False,
                    "error": f"角度调整失败：{result['error']}"
                }
        except Exception as e:
            logger.error(f"调整舵机失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_servo_name(self, servo_code: str) -> str:
        """获取舵机名称"""
        return SERVO_NAME.get(servo_code, "未知")

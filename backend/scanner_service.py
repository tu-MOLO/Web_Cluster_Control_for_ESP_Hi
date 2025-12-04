import requests
import socket
from concurrent.futures import ThreadPoolExecutor
import json
import os
import sys
import logging

logger = logging.getLogger(__name__)

# 扫描配置
SCAN_PORT = 80
SCAN_TIMEOUT = 0.8
SCAN_THREADS = 50

# 设备文件路径，支持PyInstaller打包
if getattr(sys, 'frozen', False):
    # PyInstaller打包环境
    DEVICES_FILE = os.path.join(os.path.dirname(sys.executable), "devices.json")
else:
    # 开发环境
    DEVICES_FILE = os.path.join(os.path.dirname(__file__), "devices.json")


class ScannerService:
    """设备扫描服务"""
    
    def __init__(self):
        self.devices_file = DEVICES_FILE

    def get_local_ip(self) -> str:
        """获取本机IP"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(0.1)
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "192.168.1.1"

    def get_scan_range(self) -> list:
        """生成完整IP范围（1-254）"""
        local_ip = self.get_local_ip()
        logger.info(f"本机IP: {local_ip}")
        try:
            prefix = ".".join(local_ip.split(".")[:3])
            return [f"{prefix}.{i}" for i in range(1, 255)]
        except:
            return [f"192.168.1.{i}" for i in range(1, 255)]

    def scan_single_ip(self, ip: str) -> str:
        """扫描单个IP是否为目标设备"""
        try:
            url = f"http://{ip}:{SCAN_PORT}/control"
            headers = {
                "Accept": "*/*",
                "Connection": "close",  # 显式关闭连接
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
            
            # 尝试直接连接IP
            response = requests.post(
                url=url,
                data='{}',
                headers=headers,
                timeout=SCAN_TIMEOUT,
                verify=False,
                allow_redirects=False
            )
            
            if response.status_code == 200 and response.text == '{"code":200}':
                logger.info(f"发现设备: {ip}")
                return ip
                
        except:
            pass
        
        return None

    def scan_devices(self) -> list:
        """扫描局域网内的所有设备"""
        logger.info("开始扫描局域网...")
        ip_range = self.get_scan_range()
        found_devices = []
        
        from concurrent.futures import as_completed
        
        total = len(ip_range)
        completed = 0
        
        with ThreadPoolExecutor(max_workers=SCAN_THREADS) as executor:
            # 提交所有任务
            futures = {executor.submit(self.scan_single_ip, ip): ip for ip in ip_range}
            
            # 处理完成的任务
            for future in as_completed(futures):
                completed += 1
                if completed % 50 == 0:
                    logger.info(f"扫描进度: {completed}/{total}")
                
                result = future.result()
                if result and result not in found_devices:
                    found_devices.append(result)
        
        logger.info(f"扫描完成，共发现 {len(found_devices)} 个设备")
        return found_devices

    def remove_device(self, ip: str) -> bool:
        """从列表中移除设备"""
        try:
            if os.path.exists(self.devices_file):
                with open(self.devices_file, 'r') as f:
                    devices = json.load(f)
                
                if ip in devices:
                    devices.remove(ip)
                    with open(self.devices_file, 'w') as f:
                        json.dump(devices, f)
                    return True
            return False
        except Exception as e:
            logger.error(f"删除设备失败: {e}")
            return False

    def save_devices(self, devices: list):
        """保存设备列表到文件"""
        try:
            with open(self.devices_file, "w") as f:
                json.dump(devices, f, indent=2)
            logger.info(f"设备列表已保存到 {self.devices_file}")
        except Exception as e:
            logger.error(f"保存设备列表失败: {str(e)}")
            raise

    def load_devices(self) -> list:
        """从文件加载设备列表"""
        try:
            if not os.path.exists(self.devices_file):
                logger.warning(f"设备列表文件不存在: {self.devices_file}")
                return []
            
            with open(self.devices_file, "r") as f:
                devices = json.load(f)
            
            logger.info(f"从文件加载了 {len(devices)} 个设备")
            return devices
        except Exception as e:
            logger.error(f"加载设备列表失败: {str(e)}")
            return []

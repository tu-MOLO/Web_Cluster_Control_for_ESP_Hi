import requests
import socket
from concurrent.futures import ThreadPoolExecutor
import json
import os
import sys
import logging

logger = logging.getLogger(__name__)

# 扫描配置
SCAN_PORT = 80  # ESP-HI设备HTTP服务端口
SCAN_TIMEOUT_SECONDS = 0.8  # 单设备扫描超时时间（秒），根据网络延迟调整
SCAN_THREADS = 50  # 并发扫描线程数，建议根据网络带宽和设备性能调整

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
                timeout=SCAN_TIMEOUT_SECONDS,
                verify=False,
                allow_redirects=False
            )
            
            if response.status_code == 200 and response.text == '{"code":200}':
                logger.info(f"发现设备: {ip}")
                return ip
                
        except Exception as e:
            logger.debug(f"扫描 {ip} 失败: {str(e)}")
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
                
                # 支持新旧格式
                new_devices = []
                found = False
                for device in devices:
                    if isinstance(device, dict):
                        if device.get('ip') != ip:
                            new_devices.append(device)
                        else:
                            found = True
                    else:
                        # 旧格式（纯IP字符串）
                        if device != ip:
                            new_devices.append({'ip': device, 'name': None})
                        else:
                            found = True
                
                if found:
                    with open(self.devices_file, 'w') as f:
                        json.dump(new_devices, f, indent=2)
                    return True
            return False
        except Exception as e:
            logger.error(f"删除设备失败: {e}")
            return False

    def save_devices(self, devices: list):
        """保存设备列表到文件，仅新增不存在的记录"""
        try:
            # 先加载现有设备列表
            existing_devices = self.load_devices()
            
            # 创建现有设备IP的集合，用于快速查找
            existing_ips = {d['ip'] if isinstance(d, dict) else d for d in existing_devices}
            
            # 标准化现有设备为对象格式
            normalized_existing = []
            for device in existing_devices:
                if isinstance(device, dict):
                    normalized_existing.append(device)
                else:
                    normalized_existing.append({'ip': device, 'name': None})
            
            # 过滤出新增的设备（不在现有列表中的设备）
            new_devices = normalized_existing.copy()
            for device in devices:
                device_ip = device if isinstance(device, str) else device.get('ip')
                if device_ip not in existing_ips:
                    if isinstance(device, str):
                        new_devices.append({'ip': device, 'name': None})
                    else:
                        new_devices.append(device)
                    existing_ips.add(device_ip)
            
            # 原子性保存：先写入临时文件，再重命名替换原文件
            temp_file = self.devices_file + ".tmp"
            with open(temp_file, "w") as f:
                json.dump(new_devices, f, indent=2)
            
            # 使用os.replace实现原子性替换，确保要么完全成功要么完全失败
            os.replace(temp_file, self.devices_file)
            
            logger.info(f"设备列表已保存到 {self.devices_file}，新增了 {len(new_devices) - len(normalized_existing)} 个设备")
        except Exception as e:
            logger.error(f"保存设备列表失败: {str(e)}")
            # 清理临时文件
            temp_file = self.devices_file + ".tmp"
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise

    def load_devices(self) -> list:
        """从文件加载设备列表"""
        try:
            if not os.path.exists(self.devices_file):
                logger.warning(f"设备列表文件不存在: {self.devices_file}")
                return []
            
            with open(self.devices_file, "r") as f:
                devices = json.load(f)
            
            # 标准化为对象格式（支持旧格式兼容）
            normalized_devices = []
            for device in devices:
                if isinstance(device, dict):
                    normalized_devices.append(device)
                else:
                    # 旧格式转换
                    normalized_devices.append({'ip': device, 'name': None})
            
            logger.info(f"从文件加载了 {len(normalized_devices)} 个设备")
            return normalized_devices
        except Exception as e:
            logger.error(f"加载设备列表失败: {str(e)}")
            return []

    def rename_device(self, ip: str, name: str) -> bool:
        """重命名设备"""
        try:
            if os.path.exists(self.devices_file):
                with open(self.devices_file, 'r') as f:
                    devices = json.load(f)
                
                # 标准化并更新设备名称
                updated_devices = []
                found = False
                for device in devices:
                    if isinstance(device, dict):
                        if device.get('ip') == ip:
                            device['name'] = name if name.strip() else None
                            found = True
                        updated_devices.append(device)
                    else:
                        # 旧格式转换
                        if device == ip:
                            updated_devices.append({'ip': device, 'name': name if name.strip() else None})
                            found = True
                        else:
                            updated_devices.append({'ip': device, 'name': None})
                
                if found:
                    with open(self.devices_file, 'w') as f:
                        json.dump(updated_devices, f, indent=2)
                    logger.info(f"设备 {ip} 已重命名为: {name}")
                    return True
            return False
        except Exception as e:
            logger.error(f"重命名设备失败: {e}")
            return False
    
    def add_device(self, ip: str, name: str = '') -> bool:
        """添加单个设备"""
        try:
            # 先加载现有设备
            existing_devices = self.load_devices()
            existing_ips = {device['ip'] for device in existing_devices}
            
            # 检查设备是否已存在
            if ip in existing_ips:
                logger.info(f"设备 {ip} 已存在，跳过添加")
                return False
            
            # 添加新设备
            new_device = {'ip': ip, 'name': name if name.strip() else None}
            existing_devices.append(new_device)
            
            # 保存设备列表
            with open(self.devices_file, 'w') as f:
                json.dump(existing_devices, f, indent=2)
            
            logger.info(f"成功添加设备: {ip} (名称: {name})")
            return True
        except Exception as e:
            logger.error(f"添加设备失败: {e}")
            return False

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
舵机校准控制程序

此模块提供了舵机狗设备的舵机校准功能，支持进入校准模式、调整各腿舵机角度以及保存校准结果。
校准过程中可以精确控制四个腿部（前左腿、前右腿、后左腿、后右腿）的角度参数。

依赖库：
    - requests: 用于发送HTTP请求到设备
    - json: 用于解析设备配置文件
    - sys: 提供系统相关功能
    - typing: 提供类型注解支持
"""

import requests
import json
import sys
from typing import Dict, Optional

# 配置参数
DEVICE_FILE = "devices.json"  # 存储已发现设备列表的JSON文件
HTTP_TIMEOUT = 3.0  # 超时时间延长至3秒，适配设备响应速度

# 四肢编号映射（用户输入编号到内部代码的映射）
SERVO_MAP = {
    "1": "fl",  # 前左腿
    "2": "fr",  # 前右腿
    "3": "bl",  # 后左腿
    "4": "br"   # 后右腿
}

# 内部代码到中文名称的映射（用于友好显示）
SERVO_NAME = {
    "fl": "前左腿",
    "fr": "前右腿",
    "bl": "后左腿",
    "br": "后右腿"
}

class CalibrationController:
    """
    舵机校准控制器类
    
    提供与设备进行校准相关通信的方法，包括进入校准模式、调整舵机角度和退出校准模式。
    封装了所有与设备校准相关的HTTP请求处理。
    """
    
    def __init__(self, device: str):
        """
        初始化校准控制器
        
        Args:
            device: 设备的IP地址或主机名
        """
        self.device = device  # 存储目标设备标识
        self.base_url = f"http://{device}"  # 构建设备基础URL
        
        # 配置HTTP请求头（模拟浏览器行为，确保设备能够正确响应）
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,zh-HK;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Referer": f"http://{device}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
        }
        
        # 创建并配置HTTP会话，重用连接以提高性能
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False  # 忽略SSL证书验证（开发环境）

    def _send_request(self, endpoint: str, data: Optional[Dict] = None, method: str = "POST") -> Dict:
        """
        通用请求方法，封装向设备发送HTTP请求的逻辑
        
        Args:
            endpoint: API端点路径（如"start_calibration"）
            data: 请求携带的JSON数据（可选：默认None）
            method: HTTP方法，支持"GET"或"POST"，默认为"POST"
            
        Returns:
            包含请求结果的字典，格式为{"success": bool, "response": str}或{"success": bool, "error": str}
        """
        try:
            url = f"{self.base_url}/{endpoint}"  # 构建完整请求URL
            
            # 根据指定的HTTP方法发送请求
            if method.upper() == "GET":
                response = self.session.get(url, timeout=HTTP_TIMEOUT)
            else:  # 默认使用POST方法
                response = self.session.post(url, json=data, timeout=HTTP_TIMEOUT)
            
            response.raise_for_status()  # 如果响应状态码不是200，抛出HTTPError异常
            return {"success": True, "response": response.text}  # 请求成功返回响应内容
        except Exception as e:
            return {"success": False, "error": str(e)}  # 请求失败返回错误信息

    def start_calibration(self) -> bool:
        """
        发送命令让设备进入校准模式
        
        注意：设备要求此操作必须使用GET请求
        
        Returns:
            bool: 校准模式进入成功返回True，否则返回False
        """
        print(f"→ 向设备 {self.device} 发送进入校准模式指令（GET）...")
        result = self._send_request("start_calibration", method="GET")
        
        # 根据请求结果显示不同的反馈信息
        if result["success"]:
            print("✅ 已进入校准模式（可开始调整角度）")
            return True
        else:
            print(f"❌ 进入校准模式失败：{result['error']}")
            return False

    def exit_calibration(self) -> bool:
        """
        发送命令让设备退出校准模式并保存校准结果
        
        注意：设备要求此操作必须使用GET请求
        
        Returns:
            bool: 校准模式退出成功返回True，否则返回False
        """
        print(f"→ 向设备 {self.device} 发送退出校准模式指令（GET）...")
        result = self._send_request("exit_calibration", method="GET")
        
        # 根据请求结果显示不同的反馈信息
        if result["success"]:
            print("✅ 已退出校准模式，校准结果已保存")
            return True
        else:
            print(f"❌ 退出校准模式失败：{result['error']}")
            return False

    def adjust_servo(self, servo: str, value: int) -> bool:
        """
        调整指定舵机的角度
        
        注意：设备要求此操作必须使用POST请求
        
        Args:
            servo: 舵机标识代码（如"fl"代表前左腿）
            value: 要设置的角度值，范围为-25到25
            
        Returns:
            bool: 角度调整成功返回True，否则返回False
        """
        # 验证角度值是否在有效范围内
        if not (-25 <= value <= 25):
            print("❌ 角度必须在 -25 ~ 25 之间")
            return False
        
        print(f"→ 调整 {SERVO_NAME[servo]} 角度至 {value}（POST）...")
        # 发送角度调整请求，携带舵机标识和目标角度值
        result = self._send_request("adjust", {"servo": servo, "value": value}, method="POST")
        
        # 根据请求结果显示不同的反馈信息
        if result["success"]:
            print("✅ 角度调整指令已发送")
            return True
        else:
            print(f"❌ 角度调整失败：{result['error']}")
            return False

def load_devices() -> Optional[list]:
    """
    从配置文件加载已发现的设备列表
    
    从JSON文件中读取设备IP地址列表，用于后续选择和控制。
    处理多种可能的错误情况，包括文件不存在和格式错误。
    
    Returns:
        成功加载返回设备列表（IP地址组成的列表），否则返回None
    """
    try:
        # 打开并解析设备配置文件
        with open(DEVICE_FILE, "r", encoding="utf-8") as f:
            devices = json.load(f)
        
        # 检查是否有设备信息
        if not devices:
            print(f"⚠️ {DEVICE_FILE} 中没有设备，请先运行扫描程序")
            return None
        
        return devices
    except FileNotFoundError:
        print(f"⚠️ 未找到 {DEVICE_FILE}，请先运行 scanner.py 扫描设备")
        return None
    except Exception as e:
        print(f"⚠️ 加载设备列表失败：{str(e)}")
        return None

def select_single_device(devices: list) -> Optional[str]:
    """
    让用户从设备列表中选择一个设备进行校准
    
    显示所有可用设备，接收用户输入的序号，返回对应的设备IP地址。
    包含输入验证和错误处理，支持通过输入'q'退出。
    
    Args:
        devices: 可用设备IP地址列表
        
    Returns:
        用户选择的设备IP地址，或用户退出时返回None
    """
    print("\n可用设备列表：")
    # 显示带有序号的设备列表
    for i, device in enumerate(devices):
        print(f"{i+1}. {device}")
    
    # 循环接收用户输入，直到选择有效设备或退出
    while True:
        user_input = input("\n请选择一个设备进行校准（输入序号，如1）：").strip()
        
        # 检查用户是否要退出
        if user_input.lower() == 'q':
            return None
        
        try:
            # 转换输入为索引并验证范围
            index = int(user_input) - 1
            if 0 <= index < len(devices):
                return devices[index]  # 返回选择的设备
            else:
                print(f"❌ 请输入1-{len(devices)}之间的序号")
        except ValueError:
            print("❌ 请输入有效的数字序号")

def calibration_menu(controller: CalibrationController):
    """
    显示校准操作菜单
    
    打印格式化的操作菜单，向用户展示可用的校准操作选项。
    包括调整各腿角度、完成校准退出等功能。
    
    Args:
        controller: 校准控制器实例（未在函数中直接使用，但为了接口一致性保留）
    """
    print("\n" + "="*50)
    print("          舵机校准操作菜单          ")
    print("="*50)
    print("1. 调整前左腿角度")
    print("2. 调整前右腿角度")
    print("3. 调整后左腿角度")
    print("4. 调整后右腿角度")
    print("0. 完成校准并退出（自动保存）")
    print("-"*50)
    print("提示：任何步骤输入 'q' 可立即退出程序")
    print("="*50)

def main():
    """
    程序主入口
    
    实现完整的校准流程：
    1. 加载设备列表并让用户选择要校准的设备
    2. 初始化校准控制器并进入校准模式
    3. 提供交互式菜单让用户进行舵机角度调整
    4. 处理用户退出和异常情况，确保安全退出校准模式
    """
    # 显示程序欢迎信息
    print("="*60)
    print("        舵机校准控制程序        ")
    print("="*60)
    print("说明：校准过程中可随时按 Ctrl+C 或输入 'q' 退出")
    print("="*60)

    # 1. 加载设备列表并选择单个设备
    devices = load_devices()
    if not devices:
        return  # 没有设备可校准，退出程序
    
    target_device = select_single_device(devices)
    if not target_device:
        print("👋 用户退出程序")
        return

    # 2. 初始化校准控制器并进入校准模式
    calib_controller = CalibrationController(target_device)
    if not calib_controller.start_calibration():
        print("💥 无法进入校准模式，程序退出")
        return

    # 3. 校准主循环（支持随时退出）
    try:
        while True:
            calibration_menu(calib_controller)
            choice = input("请选择操作（0-4）：").strip().lower()
            
            # 处理退出请求
            if choice == '0' or choice == 'q':
                calib_controller.exit_calibration()  # 保存校准结果
                print("👋 校准程序已退出")
                break
            
            # 处理四肢选择和角度调整
            if choice in SERVO_MAP:
                servo_code = SERVO_MAP[choice]  # 获取内部舵机代码
                servo_name = SERVO_NAME[servo_code]  # 获取中文名称
                
                # 循环接收角度输入，直到输入有效或退出
                while True:
                    angle_input = input(f"请输入{servo_name}的角度（-25~25，输入q退出）：").strip().lower()
                    if angle_input == 'q':
                        break  # 返回主菜单
                    
                    try:
                        angle = int(angle_input)
                        # 角度调整成功则返回菜单
                        if calib_controller.adjust_servo(servo_code, angle):
                            break
                    except ValueError:
                        print("❌ 请输入有效的整数")
            else:
                print("❌ 请输入0-4之间的数字")

    # 捕获Ctrl+C强制退出（添加安全退出机制）
    except KeyboardInterrupt:
        print("\n\n⚠️ 检测到强制退出，正在安全退出校准模式...")
        calib_controller.exit_calibration()  # 确保保存校准结果
        print("👋 程序已退出")
    except Exception as e:
        # 处理其他异常情况
        print(f"\n💥 程序出错：{str(e)}")
        print("正在尝试安全退出校准模式...")
        calib_controller.exit_calibration()  # 尝试保存校准结果

if __name__ == "__main__":
    """
    程序入口点检查
    
    当脚本直接运行时执行，而非被导入为模块时。
    在此处禁用SSL警告并启动主程序。
    """
    # 忽略SSL警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # 启动主程序
    main()
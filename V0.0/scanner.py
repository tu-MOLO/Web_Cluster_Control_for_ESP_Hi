#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP-Hi 设备扫描程序

此模块负责扫描局域网内的ESP-Hi设备，并将发现的设备信息保存到JSON文件中。
使用多线程并行扫描提高效率，支持通过IP地址和主机名两种方式检测设备。

依赖库：
    - requests：用于发送HTTP请求
    - socket：用于网络通信
    - concurrent.futures：用于并行执行线程
    - json：用于处理JSON数据
    - time：用于时间操作
    - os：用于操作系统相关功能
"""

import requests
import socket
from concurrent.futures import ThreadPoolExecutor
import json
import time
import os

# 扫描配置参数
SCAN_PORT = 80        # 设备服务端口
SCAN_TIMEOUT = 0.8    # 扫描超时时间（秒），平衡扫描速度和准确性
SCAN_THREADS = 100    # 扫描线程数量，提高并行扫描效率

# 文件路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # 获取脚本所在目录的绝对路径
SAVE_FILE = os.path.join(SCRIPT_DIR, "devices.json")    # 保存扫描结果的JSON文件路径

def get_local_ip():
    """
    获取本机IP地址
    
    使用UDP连接的方式获取本机IP地址，这种方法可以自动选择正确的网络接口。
    尝试连接到Google的DNS服务器(8.8.8.8)，但实际上不会发送数据包，
    只是为了确定出站网络接口的IP地址。
    
    Returns:
        str: 本机的IP地址，如果获取失败则返回默认值"192.168.1.1"
    """
    try:
        # 创建UDP套接字
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # 设置超时时间为0.1秒
            s.settimeout(0.1)
            # 连接到Google DNS服务器（不会实际发送数据）
            s.connect(("8.8.8.8", 80))
            # 获取套接字绑定的地址信息，返回元组(IP地址, 端口号)
            return s.getsockname()[0]
    except Exception as e:
        # 如果发生任何异常（如网络不可用），返回默认IP
        print(f"⚠️ 获取本机IP失败: {str(e)}，使用默认值")
        return "192.168.1.1"

def get_scan_range():
    """
    生成局域网IP扫描范围
    
    根据本机IP地址生成对应的局域网IP扫描范围，通常是同网段的所有主机地址。
    标准IPv4私有网络中，一个C类网段通常有254个可用地址（1-254）。
    
    Returns:
        list: 包含IP地址字符串的列表，范围通常是x.x.x.1到x.x.x.254
    """
    # 获取本机IP地址
    local_ip = get_local_ip()
    try:
        # 提取IP地址的前三段（网段前缀），例如"192.168.1"
        prefix = ".".join(local_ip.split(".")[:3])
        # 生成从1到254的完整IP地址列表
        return [f"{prefix}.{i}" for i in range(1, 255)]
    except Exception as e:
        # 如果解析IP地址失败，使用默认的扫描范围
        print(f"⚠️ 生成扫描范围失败: {str(e)}，使用默认范围")
        return [f"192.168.1.{i}" for i in range(1, 255)]

def scan_single_ip(ip):
    """
    扫描单个IP地址，检查是否为ESP-Hi设备
    
    通过向目标IP发送HTTP请求并验证响应来确定是否为ESP-Hi设备。
    首先尝试直接通过IP地址连接，如果失败则尝试通过主机名"esp-hi.local"连接。
    
    Args:
        ip (str): 要扫描的IP地址
    
    Returns:
        str: 如果是ESP-Hi设备，返回IP地址或主机名；否则返回None
    """
    try:
        # 构造设备控制API的URL
        url = f"http://{ip}:{SCAN_PORT}/control"
        
        # 设置HTTP请求头（模拟浏览器行为，确保设备能够正确响应）
        headers = {
            "Accept": "*/*",           # 接受所有类型的响应
            "Accept-Language": "zh-CN,zh;q=0.9,zh-HK;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/json",  # JSON格式请求体
            "Origin": "http://esp-hi.local",
            "Referer": "http://esp-hi.local/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
        }
        
        # 发送POST请求到设备的控制接口
        response = requests.post(
            url=url,
            data='{}',                # 空JSON对象作为请求体
            headers=headers,
            timeout=SCAN_TIMEOUT,     # 设置超时时间
            verify=False,             # 不验证SSL证书
            allow_redirects=False     # 不允许重定向
        )
        
        # 验证响应是否符合ESP-Hi设备的特征
        if response.status_code == 200 and response.text == '{"code":200}':
            return ip
        
        # 如果IP直接连接失败，尝试通过主机名"esp-hi.local"连接
        # 这是为了兼容设备可能通过mDNS或其他名称解析服务提供的主机名
        url = f"http://esp-hi.local:{SCAN_PORT}/control"
        response = requests.post(
            url=url,
            data='{}',
            headers=headers,
            timeout=SCAN_TIMEOUT,
            verify=False,
            allow_redirects=False
        )
        
        # 再次验证响应
        if response.status_code == 200 and response.text == '{"code":200}':
            return "esp-hi.local"
    except Exception as e:
        # 如果发生任何异常（连接超时、拒绝连接等），返回None
        # 不打印异常信息以避免日志过于冗长
        pass
    
    return None

def main():
    """
    程序主函数
    
    协调整个设备扫描过程，包括：
    1. 生成IP扫描范围
    2. 使用多线程并行扫描所有IP地址
    3. 收集和去重发现的设备
    4. 保存设备列表到文件
    5. 显示扫描结果
    """
    print("=== 设备扫描程序 ===")
    print("开始扫描局域网内的设备...（可能需要10-20秒）")
    
    # 获取需要扫描的IP范围
    ip_range = get_scan_range()
    print(f"正在扫描网段: {'.'.join(ip_range[0].split('.')[:3])}.1-{'.'.join(ip_range[0].split('.')[:3])}.254")
    
    # 存储发现的设备列表
    found_devices = []
    
    # 使用线程池进行并行扫描，提高扫描效率
    with ThreadPoolExecutor(max_workers=SCAN_THREADS) as executor:
        # 对每个IP地址应用scan_single_ip函数
        results = executor.map(scan_single_ip, ip_range)
    
    # 收集扫描结果，确保设备不重复
    for result in results:
        if result and result not in found_devices:
            found_devices.append(result)
    
    # 将设备列表保存到JSON文件
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(found_devices, f, indent=2, ensure_ascii=False)
    
    # 显示扫描结果摘要
    print(f"\n扫描完成！共发现 {len(found_devices)} 个设备：")
    for i, device in enumerate(found_devices):
        print(f"{i+1}. {device}")
    print(f"\n设备列表已保存到 {SAVE_FILE}")
    print("可运行 controller.py 进行控制")

if __name__ == "__main__":
    """
    程序入口点
    
    当直接运行此脚本时执行以下操作：
    1. 禁用urllib3的不安全请求警告（因为我们设置了verify=False）
    2. 调用main()函数启动扫描过程
    """
    # 导入urllib3模块以禁用不安全请求警告
    import urllib3
    # 禁用SSL证书验证警告，因为我们使用verify=False
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    # 启动主函数
    main()
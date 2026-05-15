#!/usr/bin/env python3
import sys
import json
import requests
import urllib.parse
from webvpn_core import WebVPN

def scan_http_ports(vpn, target_ip, ports=[80, 443, 8080, 8443, 8000, 8888]):
    """扫描HTTP端口"""
    open_ports = []
    
    for port in ports:
        # 构造URL
        if port == 443:
            url = f"https://{target_ip}"
        else:
            url = f"http://{target_ip}:{port}"
        
        try:
            # 转换URL
            webvpn_url = vpn.transform_url_to_webvpn_format(url)
            print(f"测试 {url} -> {webvpn_url}")
            
            # 发送请求
            response = vpn.session.get(webvpn_url, verify=False, timeout=10, allow_redirects=False)
            
            # 检查响应
            if response.status_code == 200:
                print(f"  [开放] 端口 {port}: HTTP {response.status_code}")
                open_ports.append(port)
            elif response.status_code == 302:
                location = response.headers.get('Location', '')
                print(f"  [开放] 端口 {port}: 重定向到 {location}")
                open_ports.append(port)
            else:
                print(f"  [过滤] 端口 {port}: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"  [过滤] 端口 {port}: 超时")
        except requests.exceptions.ConnectionError as e:
            print(f"  [关闭] 端口 {port}: 连接错误")
        except Exception as e:
            print(f"  [错误] 端口 {port}: {e}")
    
    return open_ports

def scan_paths(vpn, target_ip, port=80, paths=['/', '/login', '/admin', '/index.html', '/robots.txt']):
    """扫描常见路径"""
    found_paths = []
    
    for path in paths:
        if port == 443:
            url = f"https://{target_ip}{path}"
        else:
            url = f"http://{target_ip}:{port}{path}"
        
        try:
            webvpn_url = vpn.transform_url_to_webvpn_format(url)
            response = vpn.session.get(webvpn_url, verify=False, timeout=10, allow_redirects=False)
            
            if response.status_code == 200:
                content = response.text[:200] if response.text else ""
                print(f"  [发现] {path}: HTTP {response.status_code}, 内容: {content[:100]}...")
                found_paths.append((path, response.status_code, content))
            elif response.status_code == 302:
                location = response.headers.get('Location', '')
                print(f"  [重定向] {path}: -> {location}")
                found_paths.append((path, response.status_code, location))
            else:
                print(f"  [无] {path}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  [错误] {path}: {e}")
    
    return found_paths

def main():
    # 配置（请从配置文件或环境变量获取）
    vpn_base_url = 'https://v.hbu.cn'
    cookie_string = "your_cookie_string_here"  # 替换为实际的cookie
    target_ip = '202.206.3.95'  # 替换为目标IP
    
    # 初始化WebVPN
    vpn = WebVPN(vpn_base_url)
    vpn.set_cookies(cookie_string)
    
    # 获取IV和Key
    if not vpn.get_iv_key():
        print("获取IV和Key失败")
        sys.exit(1)
    
    print(f"开始扫描目标: {target_ip}")
    print("=" * 50)
    
    # 扫描HTTP端口
    print("\n[1] 扫描HTTP端口...")
    open_ports = scan_http_ports(vpn, target_ip)
    
    if not open_ports:
        print("未发现开放的HTTP端口")
        return
    
    print(f"\n发现开放端口: {open_ports}")
    
    # 对每个开放端口进行路径扫描
    for port in open_ports:
        print(f"\n[2] 扫描端口 {port} 的常见路径...")
        scan_paths(vpn, target_ip, port)
    
    print("\n扫描完成")

if __name__ == '__main__':
    main()
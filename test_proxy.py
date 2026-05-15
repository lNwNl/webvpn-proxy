#!/usr/bin/env python3
import sys
import json
from proxy_core import WebVPNProxy, create_proxy

def test_proxy():
    # 加载配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print(f"配置: {config}")
    
    # 创建代理
    proxy = create_proxy(config)
    print("代理实例创建成功")
    
    # 初始化
    if proxy.initialize():
        print("代理初始化成功")
        
        # 测试URL转换
        test_url = "http://example.com:8080/path?query=1"
        try:
            webvpn_url, headers, body = proxy.transform_request("GET", test_url, {})
            print(f"原始URL: {test_url}")
            print(f"WebVPN URL: {webvpn_url}")
            print(f"头部: {headers}")
            
            # 测试发送请求
            print("\n测试发送请求...")
            status_code, resp_headers, resp_body = proxy.handle_request("GET", test_url, {})
            print(f"状态码: {status_code}")
            print(f"响应头: {resp_headers}")
            print(f"响应体前200字节: {resp_body[:200]}")
            
        except Exception as e:
            print(f"测试失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("代理初始化失败")

if __name__ == '__main__':
    test_proxy()
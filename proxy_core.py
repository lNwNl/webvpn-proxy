import os
import requests
import urllib.parse
import logging
from typing import Optional, Dict, Any, Tuple
from webvpn_core import WebVPN

logger = logging.getLogger(__name__)


class WebVPNProxy:
    def __init__(self, vpn_base_url: str, username: str = None, password: str = None, cookie_string: str = None):
        self.webvpn = WebVPN(vpn_base_url)
        self.username = username
        self.password = password
        self.cookie_string = cookie_string
        self.authenticated = False
        self.iv_key_obtained = False
        
    def initialize(self) -> bool:
        """初始化代理：登录并获取IV/Key"""
        if self.cookie_string:
            self.webvpn.set_cookies(self.cookie_string)
            logger.info("已设置cookie")
        elif self.username and self.password:
            if not self.login():
                logger.error("登录失败")
                return False
        else:
            logger.error("需要提供cookie或用户名密码")
            return False
        
        # 获取IV和Key
        if not self.get_iv_key():
            logger.error("获取IV和Key失败")
            return False
        
        self.authenticated = True
        self.iv_key_obtained = True
        logger.info("代理初始化成功")
        return True
    
    def login(self) -> bool:
        """登录WebVPN"""
        if not self.username or not self.password:
            logger.error("缺少用户名或密码")
            return False
        
        success = self.webvpn.login(self.username, self.password)
        if success:
            self.authenticated = True
            logger.info("登录成功")
        return success
    
    def get_iv_key(self) -> bool:
        """获取IV和Key"""
        success = self.webvpn.get_iv_key()
        if success:
            self.iv_key_obtained = True
            logger.info("获取IV和Key成功")
        return success
    
    def check_and_relogin(self, response: requests.Response) -> bool:
        """检查响应是否需要重新登录，如果是则重新登录"""
        # 检查是否重定向到登录页面
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            if '/login' in location:
                logger.warning("检测到登录重定向，尝试重新登录")
                if self.username and self.password:
                    return self.login()
        return False
    
    def transform_request(self, method: str, url: str, headers: Dict[str, str], body: bytes = None) -> Tuple[str, Dict[str, str], bytes]:
        """转换请求为WebVPN格式
        
        Args:
            method: HTTP方法
            url: 原始URL
            headers: 请求头
            body: 请求体
            
        Returns:
            转换后的URL、头部、体
        """
        if not self.iv_key_obtained:
            raise ValueError("IV和Key未初始化")
        
        # 转换URL
        webvpn_url = self.webvpn.transform_url_to_webvpn_format(url)
        
        # 修改头部
        new_headers = headers.copy()
        # 设置Host为WebVPN服务器
        parsed_webvpn = urllib.parse.urlsplit(webvpn_url)
        new_headers['Host'] = parsed_webvpn.netloc
        # 设置Referer
        new_headers['Referer'] = self.webvpn.vpn_base_url + '/'
        # 移除代理相关头部
        new_headers.pop('Proxy-Connection', None)
        new_headers.pop('Proxy-Authorization', None)
        
        # 添加WebVPN cookie
        cookie_str = '; '.join([f"{k}={v}" for k, v in self.webvpn.session.cookies.items()])
        if cookie_str:
            new_headers['Cookie'] = cookie_str
        
        return webvpn_url, new_headers, body
    
    def send_request(self, method: str, url: str, headers: Dict[str, str], body: bytes = None, 
                    allow_redirects: bool = False) -> requests.Response:
        """发送请求到WebVPN
        
        Args:
            method: HTTP方法
            url: 原始URL
            headers: 请求头
            body: 请求体
            allow_redirects: 是否跟随重定向
            
        Returns:
            响应对象
        """
        webvpn_url, new_headers, new_body = self.transform_request(method, url, headers, body)
        
        # 发送请求
        response = self.webvpn.session.request(
            method=method,
            url=webvpn_url,
            headers=new_headers,
            data=new_body,
            allow_redirects=allow_redirects,
            verify=False
        )
        
        # 检查是否需要重新登录
        if self.check_and_relogin(response):
            # 重新登录后重试
            response = self.webvpn.session.request(
                method=method,
                url=webvpn_url,
                headers=new_headers,
                data=new_body,
                allow_redirects=allow_redirects,
                verify=False
            )
        
        return response
    
    def handle_request(self, method: str, url: str, headers: Dict[str, str], body: bytes = None) -> Tuple[int, Dict[str, str], bytes]:
        """处理请求并返回响应
        
        Args:
            method: HTTP方法
            url: 原始URL
            headers: 请求头
            body: 请求体
            
        Returns:
            状态码、响应头、响应体
        """
        try:
            response = self.send_request(method, url, headers, body)
            return response.status_code, dict(response.headers), response.content
        except Exception as e:
            logger.error(f"请求处理失败: {e}")
            raise


# 便捷函数
def create_proxy(config: dict = None, use_env: bool = True) -> WebVPNProxy:
    """从配置创建代理实例
    
    Args:
        config: 配置字典，如果为None则从环境变量加载
        use_env: 是否从环境变量加载配置（环境变量优先级高于config）
    
    Returns:
        WebVPNProxy实例
    """
    if config is None:
        config = {}
    
    # 从环境变量加载配置
    if use_env:
        env_mapping = {
            'WEBVPN_URL': 'webvpn_url',
            'WEBVPN_USERNAME': 'username',
            'WEBVPN_PASSWORD': 'password',
            'WEBVPN_COOKIE': 'cookie',
        }
        
        for env_var, config_key in env_mapping.items():
            value = os.environ.get(env_var)
            if value is not None:
                config[config_key] = value
    
    # 设置默认值
    config.setdefault('webvpn_url', 'https://v.hbu.cn')
    
    proxy = WebVPNProxy(
        vpn_base_url=config.get('webvpn_url'),
        username=config.get('username'),
        password=config.get('password'),
        cookie_string=config.get('cookie')
    )
    return proxy


def create_proxy_from_env() -> WebVPNProxy:
    """直接从环境变量创建代理实例"""
    return create_proxy(use_env=True)
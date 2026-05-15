import logging
import json
from mitmproxy import http, ctx
from proxy_core import WebVPNProxy, create_proxy

logger = logging.getLogger(__name__)


class WebVPNAddon:
    def __init__(self):
        self.proxy = None
        self.config = None
        
    def load(self, loader):
        """加载配置"""
        loader.add_option(
            name="webvpn_config",
            typespec=str,
            default="config.json",
            help="WebVPN配置文件路径"
        )
    
    def configure(self, updated):
        """配置更新时初始化代理"""
        if "webvpn_config" in updated:
            config_path = ctx.options.webvpn_config
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self._init_proxy()
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
    
    def _init_proxy(self):
        """初始化代理"""
        if not self.config:
            logger.error("配置未加载")
            return
        
        self.proxy = create_proxy(self.config)
        if not self.proxy.initialize():
            logger.error("代理初始化失败")
            self.proxy = None
        else:
            logger.info("WebVPN代理初始化成功")
    
    def request(self, flow: http.HTTPFlow):
        """处理HTTP请求"""
        if not self.proxy:
            logger.warning("代理未初始化，跳过请求")
            return
        
        # 跳过WebVPN自身的请求
        if flow.request.pretty_host == self.proxy.webvpn.vpn_base_url.split('//')[1]:
            return
        
        # 跳过CONNECT隧道请求（HTTPS握手）
        if flow.request.method == "CONNECT":
            return
        
        try:
            # 获取原始请求信息
            method = flow.request.method
            url = flow.request.pretty_url
            headers = dict(flow.request.headers)
            body = flow.request.content
            
            logger.debug(f"处理请求: {method} {url}")
            
            # 使用代理处理请求
            status_code, resp_headers, resp_body = self.proxy.handle_request(
                method, url, headers, body
            )
            
            # 创建响应
            flow.response = http.Response.make(
                status_code,
                resp_body,
                resp_headers
            )
            
            logger.debug(f"请求完成: {status_code}")
            
        except Exception as e:
            logger.error(f"请求处理失败: {e}")
            # 返回错误响应
            flow.response = http.Response.make(
                502,
                f"WebVPN代理错误: {e}".encode(),
                {"Content-Type": "text/plain"}
            )
    
    def responseheaders(self, flow: http.HTTPFlow):
        """处理响应头（可用于修改响应头）"""
        # 移除可能干扰的头部
        if flow.response:
            flow.response.headers.pop("Content-Security-Policy", None)
            flow.response.headers.pop("X-Frame-Options", None)


addons = [WebVPNAddon()]
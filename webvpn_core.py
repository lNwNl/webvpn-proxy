import requests
import urllib.parse
import binascii
import time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class WebVPN:
    def __init__(self, vpn_base_url: str):
        self.vpn_base_url = vpn_base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
        })
        self.iv = None
        self.key = None
        self.wengine_vpn_ticketv_key = None
        self.wengine_vpn_ticketv_value = None
        self.remember_token = None

    def set_cookies(self, cookie_string: str):
        """从cookie字符串中设置cookies"""
        # 解析cookie字符串
        cookies = {}
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key] = value
        # 更新session的cookies
        self.session.cookies.update(cookies)
        # 提取wengine_vpn_ticketv键名
        self.wengine_vpn_ticketv_key = [k for k in cookies.keys() if k.startswith('wengine_vpn_ticketv')]
        if self.wengine_vpn_ticketv_key:
            self.wengine_vpn_ticketv_key = self.wengine_vpn_ticketv_key[0]
            self.wengine_vpn_ticketv_value = cookies[self.wengine_vpn_ticketv_key]

    def encrypt_password(self, password: str) -> str:
        """加密密码，使用AES-CFB模式，密钥和IV都是'wrdvpnisawesome!'
        实现与JavaScript相同的加密逻辑"""
        key = b'wrdvpnisawesome!'
        iv = b'wrdvpnisawesome!'
        
        # 填充密码到16的倍数（用'0'填充）
        segment_size = 16
        if len(password) % segment_size != 0:
            append_length = segment_size - len(password) % segment_size
            password_padded = password + '0' * append_length
        else:
            password_padded = password
        
        # 使用AES-CFB加密，segment_size=128位（16字节）
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ct = encryptor.update(password_padded.encode('utf-8')) + encryptor.finalize()
        
        # 返回IV的十六进制 + 加密字节的十六进制（截断到原始密码长度*2）
        iv_hex = binascii.hexlify(iv).decode('utf-8')
        ct_hex = binascii.hexlify(ct).decode('utf-8')
        # 截断到原始密码长度*2（每个字节2个十六进制字符）
        truncated_ct_hex = ct_hex[:len(password) * 2]
        return iv_hex + truncated_ct_hex

    def login(self, username: str, password: str) -> bool:
        """登录WebVPN，获取必要的cookies"""
        # 先访问登录页面获取cookies
        login_url = f"{self.vpn_base_url}/login"
        resp = self.session.get(login_url, verify=False)
        if resp.status_code != 200:
            print(f"访问登录页面失败: {resp.status_code}")
            return False
        
        # 提取wengine_vpn_ticketv键名
        cookies = self.session.cookies.get_dict()
        self.wengine_vpn_ticketv_key = [k for k in cookies.keys() if k.startswith('wengine_vpn_ticketv')]
        if self.wengine_vpn_ticketv_key:
            self.wengine_vpn_ticketv_key = self.wengine_vpn_ticketv_key[0]
            self.wengine_vpn_ticketv_value = cookies[self.wengine_vpn_ticketv_key]
        
        # 加密密码
        encrypted_password = self.encrypt_password(password)
        
        # 构造登录数据
        data = {
            'auth_type': 'local',
            'username': username,
            'password': encrypted_password,
            'sms_code': '',
            'remember_cookie': 'on',
            'needCaptcha': 'false',
            'captcha_id': 'TRFZV17vglAnG68',
            'captcha': '',
        }
        
        # 发送登录请求
        login_api = f"{self.vpn_base_url}/do-login"
        resp = self.session.post(login_api, data=data, verify=False, allow_redirects=False)
        
        if resp.status_code == 200:
            try:
                result = resp.json()
                if result.get('success'):
                    print("登录成功")
                    # 从响应中提取remember_token
                    if 'remember_token' in result:
                        self.remember_token = result['remember_token']
                    # 更新cookies
                    cookies = self.session.cookies.get_dict()
                    if self.wengine_vpn_ticketv_key in cookies:
                        self.wengine_vpn_ticketv_value = cookies[self.wengine_vpn_ticketv_key]
                    return True
                else:
                    print(f"登录失败: {result.get('error', '未知错误')}")
                    return False
            except Exception as e:
                print(f"解析登录响应失败: {e}")
                return False
        else:
            print(f"登录请求失败: {resp.status_code}")
            return False

    def get_iv_key(self) -> bool:
        """获取IV和Key，用于URL加密"""
        url = f"{self.vpn_base_url}/user/info"
        timestamp = str(int(round(time.time() * 1000)))
        params = {'_t': timestamp}
        
        resp = self.session.get(url, params=params, verify=False, allow_redirects=False)
        if resp.status_code == 200:
            data = resp.json()
            self.iv = data.get('wrdvpnIV', '').encode('utf-8')
            self.key = data.get('wrdvpnKey', '').encode('utf-8')
            return True
        else:
            print(f"获取IV和Key失败: {resp.status_code}")
            return False

    def encrypt_hostname(self, hostname: str) -> str:
        """加密主机名，使用AES-CFB模式，密钥和IV从user/info获取"""
        if not self.iv or not self.key:
            raise ValueError("IV和Key未初始化，请先调用get_iv_key()")
        
        # 使用AES-CFB加密，segment_size=128位（16字节）
        cipher = Cipher(algorithms.AES(self.key), modes.CFB(self.iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ct = encryptor.update(hostname.encode('utf-8')) + encryptor.finalize()
        return binascii.hexlify(ct).decode('utf-8')

    def transform_url_to_webvpn_format(self, target_url: str) -> str:
        """将普通URL转换为WebVPN格式的URL"""
        parsed_url = urllib.parse.urlsplit(target_url)
        scheme = parsed_url.scheme
        if scheme not in ['http', 'https']:
            raise ValueError('scheme must be http or https')
        
        netloc = parsed_url.netloc
        hostname = netloc.split(':')[0]
        port = '-' + netloc.split(':')[1] if ':' in netloc else ''
        path = parsed_url.path
        query = '?' + parsed_url.query if parsed_url.query else ''
        fragment = '#' + parsed_url.fragment if parsed_url.fragment else ''
        
        # 加密主机名
        encrypted_hostname = self.encrypt_hostname(hostname)
        # 构造WebVPN格式的URL
        webvpn_url = f"{self.vpn_base_url}/{scheme}{port}/{self.iv.hex()}{encrypted_hostname}{path}{query}{fragment}"
        return webvpn_url
    
    def get_cookie_string(self) -> str:
        """获取当前cookie字符串"""
        cookies = self.session.cookies.get_dict()
        return '; '.join([f"{k}={v}" for k, v in cookies.items()])


if __name__ == '__main__':
    # 测试代码
    vpn_base_url = 'https://v.hbu.cn'
    vpn = WebVPN(vpn_base_url)
    
    # 这里需要用户提供用户名和密码
    # username = 'your_username'
    # password = 'your_password'
    # if vpn.login(username, password):
    #     if vpn.get_iv_key():
    #         test_url = 'http://example.com:8080/path?query=1'
    #         webvpn_url = vpn.transform_url_to_webvpn_format(test_url)
    #         print(f"原始URL: {test_url}")
    #         print(f"WebVPN URL: {webvpn_url}")
#!/usr/bin/env python3
import sys
import os
import json
import argparse
import logging
from pathlib import Path

def setup_logging(level: str = "INFO"):
    """设置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('webvpn_proxy.log')
        ]
    )

def load_config_from_env(config: dict) -> dict:
    """从环境变量加载配置，覆盖现有配置"""
    env_mapping = {
        'WEBVPN_URL': 'webvpn_url',
        'WEBVPN_USERNAME': 'username',
        'WEBVPN_PASSWORD': 'password',
        'WEBVPN_COOKIE': 'cookie',
        'WEBVPN_PROXY_PORT': 'proxy_port',
        'WEBVPN_LOG_LEVEL': 'log_level',
        'WEBVPN_SSL_INSECURE': 'ssl_insecure',
    }
    
    for env_var, config_key in env_mapping.items():
        value = os.environ.get(env_var)
        if value is not None:
            # 类型转换
            if config_key == 'proxy_port':
                try:
                    value = int(value)
                except ValueError:
                    continue
            elif config_key == 'ssl_insecure':
                value = value.lower() in ('true', '1', 'yes', 'on')
            
            config[config_key] = value
    
    return config

def main():
    parser = argparse.ArgumentParser(description='WebVPN代理服务器')
    parser.add_argument('-c', '--config', default='config.json', help='配置文件路径')
    parser.add_argument('-p', '--port', type=int, help='代理端口（覆盖配置文件）')
    parser.add_argument('-l', '--log-level', default='INFO', help='日志级别')
    parser.add_argument('--listen', default='0.0.0.0', help='监听地址')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # 加载配置文件
    config = {}
    config_path = Path(args.config)
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"已加载配置文件: {config_path}")
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}，使用默认配置")
    else:
        logger.info(f"配置文件不存在: {config_path}，使用默认配置")
    
    # 从环境变量加载配置
    config = load_config_from_env(config)
    
    # 命令行参数覆盖
    if args.port:
        config['proxy_port'] = args.port
    if args.log_level:
        config['log_level'] = args.log_level
    
    # 设置默认值
    config.setdefault('webvpn_url', 'https://v.hbu.cn')
    config.setdefault('proxy_port', 8080)
    config.setdefault('log_level', 'INFO')
    config.setdefault('ssl_insecure', True)
    
    # 更新配置文件路径（供mitmproxy addon使用）
    config['config_file'] = str(config_path.absolute()) if config_path.exists() else None
    
    # 如果配置文件存在，保存更新后的配置
    if config_path.exists():
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存配置文件失败: {e}")
    
    logger.info(f"WebVPN代理启动中...")
    logger.info(f"监听地址: {args.listen}:{config.get('proxy_port', 8080)}")
    logger.info(f"WebVPN地址: {config.get('webvpn_url')}")
    logger.info(f"日志级别: {config.get('log_level')}")
    
    # 启动mitmproxy
    try:
        from mitmproxy.tools.main import mitmdump
        import sys
        
        # 构建mitmproxy参数
        mitm_args = [
            '--listen-port', str(config.get('proxy_port', 8080)),
            '--listen-host', args.listen,
            '--ssl-insecure' if config.get('ssl_insecure', True) else '',
            '--scripts', 'webvpn_proxy.py'
        ]
        
        # 如果配置文件存在，传递给mitmproxy
        if config_path.exists():
            mitm_args.extend(['--set', f'webvpn_config={config_path.absolute()}'])
        
        # 过滤空字符串
        mitm_args = [arg for arg in mitm_args if arg]
        
        logger.info(f"mitmproxy参数: {mitm_args}")
        
        # 启动
        sys.argv = ['mitmdump'] + mitm_args
        mitmdump()
        
    except ImportError:
        logger.error("mitmproxy未安装，请运行: uv add mitmproxy")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("代理已停止")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
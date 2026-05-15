#!/usr/bin/env python3
import sys
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
    
    # 加载配置
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        sys.exit(1)
    
    # 覆盖端口
    if args.port:
        config['proxy_port'] = args.port
    
    # 更新配置文件路径（供mitmproxy addon使用）
    config['config_file'] = str(config_path.absolute())
    
    # 保存更新后的配置
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    logger.info(f"WebVPN代理启动中...")
    logger.info(f"监听地址: {args.listen}:{config.get('proxy_port', 8080)}")
    logger.info(f"WebVPN地址: {config.get('webvpn_url')}")
    
    # 启动mitmproxy
    try:
        from mitmproxy.tools.main import mitmdump
        import sys
        
        # 构建mitmproxy参数
        mitm_args = [
            '--listen-port', str(config.get('proxy_port', 8080)),
            '--listen-host', args.listen,
            '--set', f'webvpn_config={config_path.absolute()}',
            '--ssl-insecure' if config.get('ssl_insecure', True) else '',
            '--scripts', 'webvpn_proxy.py'
        ]
        
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
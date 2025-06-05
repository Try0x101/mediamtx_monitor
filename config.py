# config.py
"""
Configuration and constants for MediaMTX Monitor application.
Contains all settings, API endpoints, and default values.
"""

from urllib.parse import urlparse

# API Configuration
API_BASE_URL = "http://188.132.234.72:9997/v3"
REFRESH_INTERVAL_MS = 1000  # Global refresh interval in milliseconds
API_HOST = urlparse(API_BASE_URL).hostname

# Default ports for different protocols
DEFAULT_PORTS = {
    "hls": "8888",
    "rtsp": "8554",
    "rtmp": "1935",
    "webrtc": "8889"
}

# Default settings for automatic management
DEFAULT_SETTINGS = {
    "auto_restart_enabled": False,
    "packet_loss_threshold": 5.0,  # Packet loss percentage
    "monitor_interval": 30,  # Check interval in seconds
    "restart_cooldown": 300,  # Time between restarts in seconds
    "max_rtt_threshold": 1000,  # Maximum RTT in milliseconds
    "min_bandwidth_threshold": 0.1,  # Minimum bandwidth in Mbps
    "buffer_size_threshold": 1048576,  # Maximum buffer size in bytes (1MB)
    "consecutive_failures": 3  # Number of consecutive checks above threshold
}

# Navigation items for the web interface
NAV_ITEMS = {
    "global": "Global Config",
    "paths": "Paths List",
    "active_streams": "Active Streams",
    "recordings": "Recordings",
    "rtsp_conns": "RTSP Connections",
    "rtmp_conns": "RTMP Connections",
    "srt_conns": "SRT Connections",
    "srt_conns_readable": "SRT Connections (Readable)",
    "webrtc_sessions": "WebRTC Sessions",
    "hls_muxers": "HLS Muxers",
    "auto_restart_settings": "Auto-Restart Settings",
    "monitoring_dashboard": "Monitoring Dashboard"
}

# MediaMTX API endpoints
MTX_API_ENDPOINTS = {
    "global": "/config/global/get",
    "paths": "/paths/list",
    "recordings": "/recordings/list",
    "rtsp_conns": "/rtspconns/list",
    "rtmp_conns": "/rtmpconns/list",
    "srt_conns": "/srtconns/list",
    "webrtc_sessions": "/webrtcsessions/list",
    "hls_muxers": "/hlsmuxers/list"
}

# File and logging configuration
SETTINGS_FILE = "auto_restart_settings.json"
MAX_DEBUG_ENTRIES = 100  # Maximum number of debug log entries
MAX_TRIGGER_ENTRIES = 50  # Maximum number of trigger history entries
# api.py
"""
API routes and endpoints for MediaMTX Monitor application.
Handles all /api/* routes and data processing for the web interface.
"""

import requests
from flask import Blueprint, jsonify, request
from config import API_BASE_URL, MTX_API_ENDPOINTS, API_HOST, DEFAULT_PORTS
from monitoring import (
    connection_history, start_monitoring, stop_monitoring, 
    get_monitoring_status, restart_srt_connection, clear_connection_history
)
from utils import (
    debug_log, trigger_history, load_settings, save_settings,
    clear_debug_log, clear_trigger_history, add_debug_log, add_trigger_event
)

# Create API Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/data/<section_key>')
def api_data_proxy(section_key):
    """Proxy requests to MediaMTX API endpoints"""
    if section_key not in MTX_API_ENDPOINTS:
        return jsonify({"error": "Unknown section for data API"}), 404
    try:
        r = requests.get(API_BASE_URL + MTX_API_ENDPOINTS[section_key], timeout=3)
        r.raise_for_status()
        return jsonify(r.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Request error: {str(e)}"}), 500
    except ValueError:
        return jsonify({"error": "Failed to decode JSON from API response"}), 500

@api_bp.route('/active_streams_data')
def api_active_streams_data():
    """Get active streams data with playback URLs"""
    try:
        paths_endpoint = MTX_API_ENDPOINTS.get("paths")
        if not paths_endpoint:
            return jsonify({"error": "Paths endpoint not configured"}), 500

        r = requests.get(API_BASE_URL + paths_endpoint, timeout=3)
        r.raise_for_status()
        data = r.json()
        
        active_streams = []
        if data and "items" in data and data["items"] is not None:
            for path_info in data["items"]:
                is_active = path_info.get('ready', False) or \
                              path_info.get('source') is not None or \
                              len(path_info.get('readers', [])) > 0
                
                if is_active:
                    stream_name = path_info.get("name")
                    if not stream_name:
                        continue

                    playback_urls = {
                        "hls": f"http://{API_HOST}:{DEFAULT_PORTS['hls']}/{stream_name}/index.m3u8",
                        "rtsp": f"rtsp://{API_HOST}:{DEFAULT_PORTS['rtsp']}/{stream_name}",
                        "rtmp": f"rtmp://{API_HOST}:{DEFAULT_PORTS['rtmp']}/{stream_name}",
                        "webrtc": f"http://{API_HOST}:{DEFAULT_PORTS['webrtc']}/{stream_name}"
                    }
                    active_streams.append({
                        "name": stream_name,
                        "source_type": path_info.get("source", {}).get("type", "N/A") if path_info.get("source") else "N/A",
                        "ready": path_info.get("ready", False),
                        "readers_count": len(path_info.get("readers", [])),
                        "playback_urls": playback_urls
                    })
        return jsonify(active_streams)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Could not connect to MediaMTX API: {str(e)}"}), 500
    except ValueError:
        return jsonify({"error": "Failed to decode JSON from MediaMTX paths API"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@api_bp.route('/srt_conns_readable_data')
def api_srt_conns_readable_data():
    """Get SRT connections data in readable format"""
    try:
        srt_endpoint = MTX_API_ENDPOINTS.get("srt_conns")
        if not srt_endpoint:
            return jsonify({"error": "SRT connections endpoint not configured"}), 500

        r = requests.get(API_BASE_URL + srt_endpoint, timeout=3)
        r.raise_for_status()
        data = r.json()
        
        srt_connections = []
        if data and "items" in data and data["items"] is not None:
            srt_connections = data["items"]
        
        return jsonify(srt_connections)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Could not connect to MediaMTX API: {str(e)}"}), 500
    except ValueError:
        return jsonify({"error": "Failed to decode JSON from MediaMTX SRT connections API"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@api_bp.route('/auto_restart_settings', methods=['GET'])
def get_auto_restart_settings():
    """Get auto-restart settings"""
    try:
        settings = load_settings()
        return jsonify(settings)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/auto_restart_settings', methods=['POST'])
def save_auto_restart_settings():
    """Save auto-restart settings"""
    try:
        settings = request.get_json()
        if save_settings(settings):
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to save settings"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/monitoring_status', methods=['GET'])
def api_monitoring_status():
    """Get monitoring status"""
    try:
        return jsonify(get_monitoring_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/start_monitoring', methods=['POST'])
def start_monitoring_api():
    """Start monitoring"""
    try:
        start_monitoring()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/stop_monitoring', methods=['POST'])
def stop_monitoring_api():
    """Stop monitoring"""
    try:
        stop_monitoring()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/connection_history', methods=['GET'])
def get_connection_history():
    """Get connection history for diagnostics"""
    try:
        return jsonify(connection_history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/test_restart/<connection_id>', methods=['POST'])
def test_restart_connection(connection_id):
    """Test restart of specific connection"""
    try:
        # Get connection information
        r = requests.get(API_BASE_URL + MTX_API_ENDPOINTS["srt_conns"], timeout=5)
        r.raise_for_status()
        data = r.json()
        
        target_conn = None
        if data and "items" in data:
            for conn in data["items"]:
                if conn.get("id") == connection_id:
                    target_conn = conn
                    break
        
        if not target_conn:
            return jsonify({"error": f"Connection {connection_id} not found"}), 404
        
        path = target_conn.get("path", "unknown")
        if restart_srt_connection(connection_id, path):
            return jsonify({"success": True, "message": f"Connection {connection_id} restarted successfully"})
        else:
            return jsonify({"error": f"Failed to restart connection {connection_id}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/clear_history', methods=['POST'])
def api_clear_history():
    """Clear connection history"""
    try:
        clear_connection_history()
        return jsonify({"success": True, "message": "Connection history cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/restart_all_problematic', methods=['POST'])
def restart_all_problematic_connections():
    """Restart all problematic connections"""
    try:
        # Get current SRT connections
        r = requests.get(API_BASE_URL + MTX_API_ENDPOINTS["srt_conns"], timeout=5)
        r.raise_for_status()
        data = r.json()
        
        if not data or "items" not in data or not data["items"]:
            return jsonify({"error": "No SRT connections found"}), 404
        
        problematic_connections = []
        for conn in data["items"]:
            conn_id = conn.get("id")
            if conn_id and conn_id in connection_history and connection_history[conn_id]["failure_count"] > 0:
                problematic_connections.append(conn)
        
        if not problematic_connections:
            return jsonify({"message": "No problematic connections found", "restarted": 0})
        
        success_count = 0
        fail_count = 0
        
        add_debug_log(f"Starting bulk restart of {len(problematic_connections)} problematic connections", "INFO")
        
        for conn in problematic_connections:
            conn_id = conn.get("id")
            path = conn.get("path", "unknown")
            
            if restart_srt_connection(conn_id, path):
                success_count += 1
                # Reset counter after successful restart
                if conn_id in connection_history:
                    connection_history[conn_id]["failure_count"] = 0
                    connection_history[conn_id]["last_restart"] = datetime.now()
                add_trigger_event(conn_id, path, "bulk_restart", 0, 0, "success")
            else:
                fail_count += 1
                add_trigger_event(conn_id, path, "bulk_restart", 0, 0, "failure")
        
        add_debug_log(f"Bulk restart completed: {success_count} successful, {fail_count} failed", "INFO")
        
        return jsonify({
            "success": True,
            "message": f"Restart completed: {success_count} successful, {fail_count} failed",
            "restarted": success_count,
            "failed": fail_count
        })
        
    except Exception as e:
        add_debug_log(f"Error restarting all problematic connections: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/debug_log', methods=['GET'])
def get_debug_log():
    """Get debug log"""
    try:
        # Return entries in reverse order (newest first)
        return jsonify(list(reversed(debug_log)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/trigger_history', methods=['GET'])
def get_trigger_history():
    """Get trigger history"""
    try:
        # Return entries in reverse order (newest first)
        return jsonify(list(reversed(trigger_history)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/clear_debug_log', methods=['POST'])
def api_clear_debug_log():
    """Clear debug log"""
    try:
        clear_debug_log()
        return jsonify({"success": True, "message": "Debug log cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/clear_trigger_history', methods=['POST'])
def api_clear_trigger_history():
    """Clear trigger history"""
    try:
        clear_trigger_history()
        return jsonify({"success": True, "message": "Trigger history cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
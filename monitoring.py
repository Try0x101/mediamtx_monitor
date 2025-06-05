# monitoring.py
"""
Monitoring logic and background workers for MediaMTX Monitor application.
Handles SRT connection monitoring, automatic restarts, and health checks.
"""

import threading
import time
import requests
from datetime import datetime, timedelta
from config import API_BASE_URL, MTX_API_ENDPOINTS
from utils import load_settings, add_debug_log, add_trigger_event

# Global monitoring variables
monitoring_thread = None
monitoring_active = False
connection_history = {}  # Connection history for tracking consecutive failures

def restart_srt_connection(connection_id, path):
    """Restart SRT connection by kicking it"""
    try:
        # Attempt to close connection
        close_url = f"{API_BASE_URL}/srtconns/kick/{connection_id}"
        add_debug_log(f"Attempting to kick SRT connection {connection_id} for path {path}", "INFO")
        response = requests.post(close_url, timeout=5)
        add_debug_log(f"Kicked SRT connection {connection_id} for path {path}. Response: {response.status_code}", "INFO")
        
        if response.status_code == 200:
            return True
        else:
            add_debug_log(f"Unexpected response code {response.status_code} when kicking connection {connection_id}", "WARNING")
            return False
    except requests.exceptions.RequestException as e:
        add_debug_log(f"Network error restarting SRT connection {connection_id}: {e}", "ERROR")
        return False
    except Exception as e:
        add_debug_log(f"Unexpected error restarting SRT connection {connection_id}: {e}", "ERROR")
        return False

def check_srt_connections():
    """Check SRT connections and restart if necessary"""
    global connection_history
    try:
        settings = load_settings()
        if not settings.get("auto_restart_enabled", False):
            add_debug_log("Auto-restart disabled, skipping check", "DEBUG")
            return

        add_debug_log("Starting SRT connections check", "DEBUG")
        
        # Get current SRT connections
        r = requests.get(API_BASE_URL + MTX_API_ENDPOINTS["srt_conns"], timeout=5)
        r.raise_for_status()
        data = r.json()
        
        if not data or "items" not in data or not data["items"]:
            add_debug_log("No SRT connections found", "DEBUG")
            return

        current_time = datetime.now()
        restart_cooldown = timedelta(seconds=settings.get("restart_cooldown", 300))
        connections_checked = len(data["items"])
        add_debug_log(f"Checking {connections_checked} SRT connections", "INFO")
        
        for conn in data["items"]:
            conn_id = conn.get("id", "unknown")
            path = conn.get("path", "unknown")
            
            # Initialize connection history if not exists
            if conn_id not in connection_history:
                connection_history[conn_id] = {
                    "failure_count": 0,
                    "last_restart": None,
                    "last_check": current_time
                }
                add_debug_log(f"New connection tracked: {conn_id} ({path})", "INFO")
            
            conn_history = connection_history[conn_id]
            should_restart = False
            restart_reasons = []
            
            # Check packet loss
            packet_loss_rate = conn.get("packetsReceivedLossRate", 0) * 100
            packet_threshold = settings.get("packet_loss_threshold", 5.0)
            if packet_loss_rate > packet_threshold:
                should_restart = True
                reason = f"Packet loss: {packet_loss_rate:.2f}% > {packet_threshold}%"
                restart_reasons.append(reason)
                add_trigger_event(conn_id, path, "packet_loss", packet_loss_rate, packet_threshold, "threshold_exceeded")
            
            # Check RTT
            rtt = conn.get("msRTT", 0)
            rtt_threshold = settings.get("max_rtt_threshold", 1000)
            if rtt > rtt_threshold:
                should_restart = True
                reason = f"High RTT: {rtt}ms > {rtt_threshold}ms"
                restart_reasons.append(reason)
                add_trigger_event(conn_id, path, "rtt", rtt, rtt_threshold, "threshold_exceeded")
            
            # Check bandwidth
            receive_rate = conn.get("mbpsReceiveRate", 0)
            bandwidth_threshold = settings.get("min_bandwidth_threshold", 0.1)
            if 0 < receive_rate < bandwidth_threshold:
                should_restart = True
                reason = f"Low bandwidth: {receive_rate:.3f}Mbps < {bandwidth_threshold}Mbps"
                restart_reasons.append(reason)
                add_trigger_event(conn_id, path, "bandwidth", receive_rate, bandwidth_threshold, "threshold_exceeded")
            
            # Check buffer size
            buffer_size = conn.get("bytesReceiveBuf", 0)
            buffer_threshold = settings.get("buffer_size_threshold", 1048576)
            if buffer_size > buffer_threshold:
                should_restart = True
                reason = f"Large buffer: {buffer_size} bytes > {buffer_threshold} bytes"
                restart_reasons.append(reason)
                add_trigger_event(conn_id, path, "buffer_size", buffer_size, buffer_threshold, "threshold_exceeded")
            
            if should_restart:
                conn_history["failure_count"] += 1
                reason_text = ", ".join(restart_reasons)
                add_debug_log(f"Connection {conn_id} ({path}) issue #{conn_history['failure_count']}: {reason_text}", "WARNING")
                
                # Check if we reached consecutive failures threshold
                consecutive_threshold = settings.get("consecutive_failures", 3)
                if conn_history["failure_count"] >= consecutive_threshold:
                    # Check cooldown
                    if (conn_history["last_restart"] is None or 
                        current_time - conn_history["last_restart"] > restart_cooldown):
                        
                        add_debug_log(f"Initiating restart for connection {conn_id} ({path}) after {conn_history['failure_count']} consecutive failures", "WARNING")
                        add_trigger_event(conn_id, path, "restart_triggered", conn_history['failure_count'], consecutive_threshold, "connection_restart")
                        
                        if restart_srt_connection(conn_id, path):
                            conn_history["last_restart"] = current_time
                            conn_history["failure_count"] = 0
                            add_debug_log(f"Successfully restarted connection {conn_id}", "INFO")
                            add_trigger_event(conn_id, path, "restart_completed", 0, 0, "success")
                        else:
                            add_debug_log(f"Failed to restart connection {conn_id}", "ERROR")
                            add_trigger_event(conn_id, path, "restart_failed", 0, 0, "failure")
                    else:
                        time_left = restart_cooldown - (current_time - conn_history["last_restart"])
                        add_debug_log(f"Connection {conn_id} in cooldown, {time_left.seconds}s remaining", "DEBUG")
            else:
                # Reset counter on good connection
                if conn_history["failure_count"] > 0:
                    add_debug_log(f"Connection {conn_id} ({path}) recovered, resetting failure count", "INFO")
                    add_trigger_event(conn_id, path, "connection_recovered", 0, 0, "failure_count_reset")
                    conn_history["failure_count"] = 0
            
            conn_history["last_check"] = current_time
        
        # Clean up history for non-existent connections
        current_connection_ids = {conn.get("id") for conn in data["items"]}
        removed_connections = []
        for conn_id in list(connection_history.keys()):
            if conn_id not in current_connection_ids:
                removed_connections.append(conn_id)
                del connection_history[conn_id]
        
        if removed_connections:
            add_debug_log(f"Removed {len(removed_connections)} disconnected connections from tracking", "INFO")
        
        add_debug_log(f"Completed SRT connections check - {connections_checked} connections processed", "DEBUG")
        
    except requests.exceptions.RequestException as e:
        add_debug_log(f"Network error in check_srt_connections: {str(e)}", "ERROR")
    except Exception as e:
        add_debug_log(f"Unexpected error in check_srt_connections: {str(e)}", "ERROR")

def monitoring_worker():
    """Background worker for monitoring"""
    global monitoring_active
    add_debug_log("Monitoring worker started", "INFO")
    while monitoring_active:
        try:
            settings = load_settings()
            if settings.get("auto_restart_enabled", False):
                add_debug_log("Running SRT connections check...", "DEBUG")
                check_srt_connections()
            else:
                add_debug_log("Auto-restart disabled, skipping check", "DEBUG")
            time.sleep(settings.get("monitor_interval", 30))
        except Exception as e:
            add_debug_log(f"Error in monitoring worker: {e}", "ERROR")
            time.sleep(30)  # Wait 30 seconds on error
    add_debug_log("Monitoring worker stopped", "INFO")

def start_monitoring():
    """Start monitoring"""
    global monitoring_thread, monitoring_active
    if not monitoring_active:
        monitoring_active = True
        monitoring_thread = threading.Thread(target=monitoring_worker, daemon=True)
        monitoring_thread.start()
        add_debug_log("Monitoring started", "INFO")

def stop_monitoring():
    """Stop monitoring"""
    global monitoring_active
    monitoring_active = False
    add_debug_log("Monitoring stopped", "INFO")

def clear_connection_history():
    """Clear connection history"""
    global connection_history
    connection_history.clear()
    add_debug_log("Connection history cleared", "INFO")

def get_monitoring_status():
    """Get current monitoring status"""
    settings = load_settings()
    return {
        "active": monitoring_active,
        "auto_restart_enabled": settings.get("auto_restart_enabled", False),
        "interval": settings.get("monitor_interval", 30)
    }
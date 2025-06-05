# utils.py
"""
Utility functions and helpers for MediaMTX Monitor application.
Contains reusable functions for settings, logging, and data formatting.
"""

import json
import os
from datetime import datetime
from config import DEFAULT_SETTINGS, SETTINGS_FILE, MAX_DEBUG_ENTRIES, MAX_TRIGGER_ENTRIES

# Global variables for logging
debug_log = []  # Debug log entries
trigger_history = []  # Trigger event history

def add_debug_log(message, level="INFO"):
    """Add entry to debug log"""
    global debug_log
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    debug_log.append({
        "timestamp": timestamp,
        "level": level,
        "message": message
    })
    
    # Limit log size
    if len(debug_log) > MAX_DEBUG_ENTRIES:
        debug_log = debug_log[-MAX_DEBUG_ENTRIES:]

def add_trigger_event(connection_id, path, trigger_type, value, threshold, action):
    """Add trigger event to history"""
    global trigger_history
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trigger_history.append({
        "timestamp": timestamp,
        "connection_id": connection_id,
        "path": path,
        "trigger_type": trigger_type,
        "value": value,
        "threshold": threshold,
        "action": action
    })
    
    # Limit trigger history size
    if len(trigger_history) > MAX_TRIGGER_ENTRIES:
        trigger_history = trigger_history[-MAX_TRIGGER_ENTRIES:]

def load_settings():
    """Load settings from file"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                loaded_settings = json.load(f)
                # Merge with default settings
                settings = DEFAULT_SETTINGS.copy()
                settings.update(loaded_settings)
                return settings
        except Exception as e:
            add_debug_log(f"Error loading settings: {e}", "ERROR")
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        add_debug_log(f"Error saving settings: {e}", "ERROR")
        return False

def clear_debug_log():
    """Clear debug log"""
    global debug_log
    debug_log.clear()
    add_debug_log("Debug log cleared manually", "INFO")

def clear_trigger_history():
    """Clear trigger history"""
    global trigger_history
    trigger_history.clear()
    add_debug_log("Trigger history cleared manually", "INFO")

def format_bytes(bytes_value):
    """Format bytes to human readable format"""
    if bytes_value == 0:
        return '0 B'
    k = 1024
    sizes = ['B', 'KB', 'MB', 'GB']
    i = int(bytes_value.bit_length() - 1) // 10
    if i >= len(sizes):
        i = len(sizes) - 1
    return f"{bytes_value / (k ** i):.2f} {sizes[i]}"

def format_duration(created_str):
    """Format duration from creation timestamp"""
    try:
        created = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
        now = datetime.now(created.tzinfo) if created.tzinfo else datetime.now()
        diff = now - created
        hours = int(diff.total_seconds() // 3600)
        minutes = int((diff.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}m"
    except Exception:
        return 'N/A'
# app.py
"""
Main Flask application for MediaMTX Monitor.
Entry point with web routes and Flask app initialization.
"""

from flask import Flask, render_template
from config import NAV_ITEMS, REFRESH_INTERVAL_MS, API_BASE_URL
from api import api_bp
from monitoring import start_monitoring
from utils import add_debug_log

# Create Flask application
app = Flask(__name__)

# Register API Blueprint
app.register_blueprint(api_bp)

@app.route('/')
def home():
    """Home page - redirects to global config view"""
    return render_template('index.html',
                         section_title=NAV_ITEMS["global"],
                         section_key="global",
                         nav_items=NAV_ITEMS,
                         current_nav_key="global",
                         refresh_interval_ms=REFRESH_INTERVAL_MS)

@app.route('/<section_key>')
def section_view(section_key):
    """Handle different section views"""
    if section_key not in NAV_ITEMS:
        return "Invalid section", 404

    # Route to specific templates for special sections
    template_mapping = {
        "active_streams": "active_streams.html",
        "srt_conns_readable": "srt_connections.html",
        "auto_restart_settings": "auto_restart.html",
        "monitoring_dashboard": "dashboard.html"
    }
    
    template = template_mapping.get(section_key, "index.html")
    
    return render_template(template,
                         section_title=NAV_ITEMS[section_key],
                         section_key=section_key,
                         nav_items=NAV_ITEMS,
                         current_nav_key=section_key,
                         refresh_interval_ms=REFRESH_INTERVAL_MS)

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('error.html', 
                         error_code=404,
                         error_message="Page not found",
                         nav_items=NAV_ITEMS), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('error.html', 
                         error_code=500,
                         error_message="Internal server error",
                         nav_items=NAV_ITEMS), 500

if __name__ == '__main__':
    # Initialize application on startup
    add_debug_log("MediaMTX Monitor application starting", "INFO")
    add_debug_log(f"API Base URL: {API_BASE_URL}", "INFO")
    add_debug_log(f"Refresh interval: {REFRESH_INTERVAL_MS}ms", "INFO")
    
    # Start monitoring worker
    start_monitoring()
    
    # Run Flask application
    app.run(host='0.0.0.0', port=5000, debug=True)
#!/usr/bin/env python3
"""
Wallpaper Light - A tool to control lights based on wallpaper colors

This script initializes and runs the wallpaper light application, which captures
the current desktop wallpaper, analyzes its colors, and controls connected
lights to match the dominant colors.
"""

import logging
import os
import sys
import time
import argparse
from configparser import ConfigParser
import socket

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.wallpaper_capture import WallpaperCapture
from src.color_analyzer import ColorAnalyzer
from src.light_controller import LightController
from src.utils import setup_logging


def load_config():
    """Load configuration from config.ini file"""
    config = ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.ini')
    
    if not os.path.exists(config_path):
        logging.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
        
    config.read(config_path)
    return config


def run_cli_mode():
    """Run the application in command-line mode"""
    # Setup logging
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'app.log')
    setup_logging(log_path)
    
    logging.info("Starting Wallpaper Light application (CLI mode)")
    
    # Load configuration
    config = load_config()
    
    # Set socket timeout for network operations
    socket.setdefaulttimeout(30)  # Increase timeout to 30 seconds
    
    # Initialize components
    try:
        wallpaper_capture = WallpaperCapture(config)
        color_analyzer = ColorAnalyzer(config)
        light_controller = LightController(config)
        
        update_interval = config.getint('General', 'update_interval', fallback=60)
        
        logging.info(f"Application initialized with update interval of {update_interval} seconds")
        
        # Main loop
        while True:
            try:
                # Capture current wallpaper
                wallpaper_image = wallpaper_capture.capture()
                
                # Analyze colors
                dominant_colors = color_analyzer.analyze(wallpaper_image)
                
                # Control lights based on colors
                light_controller.set_colors(dominant_colors)
                
                logging.info(f"Updated lights with colors: {dominant_colors}")
                
                # Wait for next update
                time.sleep(update_interval)
                
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(10)  # Wait a bit before retrying
                
    except Exception as e:
        logging.critical(f"Failed to initialize application: {e}")
        sys.exit(1)


def run_gui_mode():
    """Run the application in GUI mode"""
    try:
        import tkinter as tk
        from src.gui import WallpaperLightGUI
        
        root = tk.Tk()
        app = WallpaperLightGUI(root)
        root.mainloop()
        
    except ImportError as e:
        logging.error(f"Failed to import GUI dependencies: {e}")
        print(f"Error: Failed to import GUI dependencies: {e}")
        print("Running in CLI mode instead...")
        run_cli_mode()
    except Exception as e:
        logging.critical(f"Failed to start GUI: {e}")
        print(f"Error: Failed to start GUI: {e}")
        sys.exit(1)


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description="Wallpaper Light - Control lights based on wallpaper colors")
    parser.add_argument("--cli", action="store_true", help="Run in command-line mode (no GUI)")
    parser.add_argument("--gui", action="store_true", help="Run in GUI mode")
    
    args = parser.parse_args()
    
    # Determine mode
    if args.cli:
        run_cli_mode()
    elif args.gui:
        run_gui_mode()
    else:
        # Default: try GUI first, fall back to CLI if GUI fails
        try:
            import tkinter
            run_gui_mode()
        except ImportError:
            print("GUI dependencies not available, running in CLI mode")
            run_cli_mode()


if __name__ == "__main__":
    main() 
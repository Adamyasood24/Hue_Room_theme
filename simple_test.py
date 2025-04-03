#!/usr/bin/env python3
"""
Simple test script for the Wallpaper Light application
"""
import os
import sys
import logging
from configparser import ConfigParser

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import setup_logging

def main():
    """Test the application components"""
    # Setup logging
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'test.log')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    setup_logging(log_path)
    
    logging.info("Starting Wallpaper Light test")
    
    # Test imports
    try:
        logging.info("Testing imports...")
        
        # Test numpy
        logging.info("Importing numpy...")
        import numpy as np
        logging.info("numpy imported successfully")
        
        # Test PIL
        logging.info("Importing PIL...")
        from PIL import Image
        logging.info("PIL imported successfully")
        
        # Test sklearn
        logging.info("Importing sklearn...")
        from sklearn.cluster import KMeans
        logging.info("sklearn imported successfully")
        
        # Test our modules
        logging.info("Importing wallpaper_capture...")
        from src.wallpaper_capture import WallpaperCapture
        logging.info("wallpaper_capture imported successfully")
        
        logging.info("Importing color_analyzer...")
        from src.color_analyzer import ColorAnalyzer
        logging.info("color_analyzer imported successfully")
        
        logging.info("Importing light_controller...")
        from src.light_controller import LightController
        logging.info("light_controller imported successfully")
        
        logging.info("All imports successful!")
        
    except ImportError as e:
        logging.error(f"Import error: {e}")
        print(f"Error: {e}")
        print("Please run 'python install_dependencies.py' to install all required dependencies")
        return
    
    print("All tests passed! The application should be ready to run.")
    print("Run the application with: python main.py")

if __name__ == "__main__":
    main() 
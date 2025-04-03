#!/usr/bin/env python3
"""
Script to install all required dependencies for the Wallpaper Light application
"""
import subprocess
import sys
import os

def install_dependencies():
    """Install all required dependencies"""
    print("Installing dependencies...")
    
    # Install Python packages
    requirements_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
    
    # Check if we need to install system dependencies
    import platform
    system = platform.system()
    
    if system == "Linux":
        print("\nYou may need to install ImageMagick for Linux wallpaper capture:")
        print("  For Debian/Ubuntu: sudo apt-get install imagemagick")
        print("  For CentOS/RHEL/Fedora: sudo yum install ImageMagick")
    
    print("\nAll dependencies installed successfully!")
    print("You can now run the application with: python main.py")

if __name__ == "__main__":
    install_dependencies() 
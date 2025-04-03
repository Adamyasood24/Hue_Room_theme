"""
Module for capturing the current desktop wallpaper
"""
import logging
import os
import platform
import tempfile
from PIL import Image


class WallpaperCapture:
    """Class to capture the current desktop wallpaper"""
    
    def __init__(self, config):
        """
        Initialize the wallpaper capture module
        
        Args:
            config: ConfigParser object with application configuration
        """
        self.config = config
        self.system = platform.system()
        self.use_screenshot = config.getboolean('WallpaperCapture', 'use_screenshot', fallback=False)
        self.capture_region = None
        
        # Try to load saved region
        if self.config.has_option('WallpaperCapture', 'region'):
            region_str = self.config.get('WallpaperCapture', 'region')
            try:
                self.capture_region = tuple(map(int, region_str.split(',')))
                logging.info(f"Loaded capture region: {self.capture_region}")
            except:
                logging.warning("Failed to parse saved region, using full screen")
                
        logging.info(f"Initializing wallpaper capture for {self.system} (Screenshot mode: {self.use_screenshot})")
    
    def capture(self):
        """
        Capture the current desktop wallpaper or screenshot
        
        Returns:
            PIL.Image: The captured wallpaper image
        """
        if self.use_screenshot:
            return self.capture_screenshot()
            
        if self.system == "Windows":
            return self._capture_windows()
        elif self.system == "Darwin":  # macOS
            return self._capture_macos()
        elif self.system == "Linux":
            return self._capture_linux()
        else:
            raise NotImplementedError(f"Unsupported operating system: {self.system}")
    
    def capture_screenshot(self):
        """
        Capture a screenshot of the entire screen
        
        Returns:
            PIL.Image: The captured screenshot
        """
        logging.debug("Capturing screenshot")
        
        # Capture full screenshot first
        if self.system == "Windows":
            full_screenshot = self._capture_screenshot_windows()
        elif self.system == "Darwin":  # macOS
            full_screenshot = self._capture_screenshot_macos()
        elif self.system == "Linux":
            full_screenshot = self._capture_screenshot_linux()
        else:
            raise NotImplementedError(f"Unsupported operating system for screenshots: {self.system}")
            
        # If we have a region, crop the screenshot
        if self.capture_region and len(self.capture_region) == 4:
            try:
                x1, y1, x2, y2 = self.capture_region
                cropped = full_screenshot.crop((x1, y1, x2, y2))
                logging.debug(f"Cropped screenshot to region {self.capture_region}")
                return cropped
            except Exception as e:
                logging.error(f"Failed to crop screenshot: {e}")
                
        return full_screenshot
    
    def set_capture_region(self, region):
        """
        Set the region to capture
        
        Args:
            region: (x1, y1, x2, y2) tuple or None for full screen
        """
        self.capture_region = region
        
        # Save the region to config
        if region:
            region_str = ','.join(map(str, region))
            self.config.set('WallpaperCapture', 'region', region_str)
        elif self.config.has_option('WallpaperCapture', 'region'):
            self.config.remove_option('WallpaperCapture', 'region')
            
        logging.info(f"Set capture region to {region}")
    
    def _capture_screenshot_windows(self):
        """Capture screenshot on Windows"""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            return screenshot
        except ImportError:
            logging.error("pyautogui not installed. Install with: pip install pyautogui")
            # Fallback to PIL-based screenshot if available
            try:
                from PIL import ImageGrab
                screenshot = ImageGrab.grab()
                return screenshot
            except Exception as e:
                logging.error(f"Failed to capture screenshot: {e}")
                # Return a blank image as fallback
                return Image.new('RGB', (800, 600), color='black')
    
    def _capture_screenshot_macos(self):
        """Capture screenshot on macOS"""
        import subprocess
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
        
        subprocess.run(['screencapture', '-x', tmp_path], check=True)
        return Image.open(tmp_path)
    
    def _capture_screenshot_linux(self):
        """Capture screenshot on Linux"""
        import subprocess
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
        
        subprocess.run(['import', '-window', 'root', tmp_path], check=True)
        return Image.open(tmp_path)
    
    def _capture_windows(self):
        """Capture wallpaper on Windows"""
        import ctypes
        from ctypes import wintypes
        
        SPI_GETDESKWALLPAPER = 0x0073
        MAX_PATH = 260
        
        path_buffer = ctypes.create_unicode_buffer(MAX_PATH)
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETDESKWALLPAPER, 
            MAX_PATH, 
            path_buffer, 
            0
        )
        
        wallpaper_path = path_buffer.value
        logging.debug(f"Windows wallpaper path: {wallpaper_path}")
        
        return Image.open(wallpaper_path)
    
    def _capture_macos(self):
        """Capture wallpaper on macOS"""
        import subprocess
        
        script = '''
        tell application "System Events"
            tell every desktop
                get picture
            end tell
        end tell
        '''
        
        proc = subprocess.Popen(['osascript', '-e', script], stdout=subprocess.PIPE)
        output, _ = proc.communicate()
        wallpaper_path = output.decode('utf-8').strip()
        logging.debug(f"macOS wallpaper path: {wallpaper_path}")
        
        return Image.open(wallpaper_path)
    
    def _capture_linux(self):
        """Capture wallpaper on Linux"""
        import subprocess
        
        # Try to get wallpaper path from GNOME
        try:
            cmd = ['gsettings', 'get', 'org.gnome.desktop.background', 'picture-uri']
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            output, _ = proc.communicate()
            wallpaper_path = output.decode('utf-8').strip().replace("'file://", "").rstrip("'")
            
            logging.debug(f"Linux wallpaper path: {wallpaper_path}")
            return Image.open(wallpaper_path)
            
        except Exception as e:
            logging.error(f"Failed to get Linux wallpaper: {e}")
            # Fallback to a screenshot
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
            
            subprocess.run(['import', '-window', 'root', tmp_path])
            return Image.open(tmp_path) 
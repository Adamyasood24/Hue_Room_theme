"""
Utility functions for the Wallpaper Light application
"""
import logging
import os
import sys
import colorsys
import tkinter as tk
from PIL import Image, ImageTk


def setup_logging(log_path=None):
    """
    Set up logging configuration
    
    Args:
        log_path: Path to log file
    """
    # Create logs directory if it doesn't exist
    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path) if log_path else logging.NullHandler()
        ]
    )


def rgb_to_hex(rgb):
    """
    Convert RGB tuple to hex color string
    
    Args:
        rgb: (R, G, B) tuple with values 0-255
        
    Returns:
        Hex color string (e.g., "#FF0000" for red)
    """
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgb(hex_color):
    """
    Convert hex color string to RGB tuple
    
    Args:
        hex_color: Hex color string (e.g., "#FF0000" for red)
        
    Returns:
        (R, G, B) tuple with values 0-255
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


class ScreenRegionSelector:
    """Class to allow the user to select a region of the screen for color analysis"""
    
    def __init__(self, parent):
        """Initialize the screen region selector"""
        self.parent = parent
        self.selection_window = None
        self.start_x = 0
        self.start_y = 0
        self.current_x = 0
        self.current_y = 0
        self.rect_id = None
        self.selected_region = None  # (x1, y1, x2, y2)
        
    def open_selector(self, screenshot):
        """
        Open the screen region selector
        
        Args:
            screenshot: PIL Image of the current screen
            
        Returns:
            Selected region as (x1, y1, x2, y2) or None if canceled
        """
        # Create a new toplevel window
        self.selection_window = tk.Toplevel(self.parent)
        self.selection_window.title("Select Screen Region")
        self.selection_window.attributes('-fullscreen', True)
        self.selection_window.attributes('-topmost', True)
        
        # Make the window semi-transparent
        self.selection_window.attributes('-alpha', 0.7)
        
        # Create a canvas to display the screenshot
        self.canvas = tk.Canvas(
            self.selection_window, 
            cursor="crosshair",
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Convert the screenshot to a PhotoImage
        self.tk_image = ImageTk.PhotoImage(screenshot)
        
        # Display the screenshot on the canvas
        self.canvas.create_image(0, 0, image=self.tk_image, anchor=tk.NW)
        
        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        # Add instructions
        self.canvas.create_text(
            screenshot.width // 2,
            20,
            text="Click and drag to select a region, or press Escape to cancel",
            fill="white",
            font=("Arial", 16)
        )
        
        # Bind escape key to cancel
        self.selection_window.bind("<Escape>", self.on_cancel)
        
        # Wait for the window to be destroyed
        self.parent.wait_window(self.selection_window)
        
        return self.selected_region
        
    def on_press(self, event):
        """Handle mouse press event"""
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        
        # Create a rectangle if it doesn't exist
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="red", width=2
        )
        
    def on_drag(self, event):
        """Handle mouse drag event"""
        self.current_x = self.canvas.canvasx(event.x)
        self.current_y = self.canvas.canvasy(event.y)
        
        # Update the rectangle
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, self.current_x, self.current_y)
        
    def on_release(self, event):
        """Handle mouse release event"""
        self.current_x = self.canvas.canvasx(event.x)
        self.current_y = self.canvas.canvasy(event.y)
        
        # Ensure coordinates are in the right order
        x1 = min(self.start_x, self.current_x)
        y1 = min(self.start_y, self.current_y)
        x2 = max(self.start_x, self.current_x)
        y2 = max(self.start_y, self.current_y)
        
        # Save the selected region
        self.selected_region = (int(x1), int(y1), int(x2), int(y2))
        
        # Close the window
        self.selection_window.destroy()
        
    def on_cancel(self, event):
        """Handle cancel event"""
        self.selected_region = None
        self.selection_window.destroy() 
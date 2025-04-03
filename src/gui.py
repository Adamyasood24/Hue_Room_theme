"""
GUI for the Wallpaper Light application
"""
import os
import sys
import logging
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from configparser import ConfigParser
from PIL import ImageTk

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.wallpaper_capture import WallpaperCapture
from src.color_analyzer import ColorAnalyzer
from src.light_controller import LightController
from src.utils import setup_logging, rgb_to_hex, hex_to_rgb, ScreenRegionSelector


class WallpaperLightGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Wallpaper Light")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Set up logging
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'app.log')
        setup_logging(log_path)
        
        # Load configuration
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.ini')
        self.config = self.load_config()
        
        # Initialize application state
        self.running = False
        self.update_thread = None
        self.current_colors = []
        self.wallpaper_image = None
        self.harmony_type_var = tk.StringVar(value="complementary")
        
        # Add screenshot mode variable
        self.screenshot_mode = tk.BooleanVar(value=self.config.getboolean('WallpaperCapture', 'use_screenshot', fallback=False))
        
        # Create GUI components
        self.create_widgets()
        
        # Initialize components to None (will be created when needed)
        self.wallpaper_capture = None
        self.color_analyzer = None
        self.light_controller = None
        self.color_preview_frames = []
        self.color_frames = []
        
        # Update status initially
        self.update_status("Ready")
        
        # Set up periodic UI updates
        self.root.after(1000, self.update_ui)

    def create_widgets(self):
        # Create a simple interface for now
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Wallpaper Light Controller", font=("Arial", 16)).pack(pady=10)
        
        # Status display
        self.status_label = ttk.Label(frame, text="Ready")
        self.status_label.pack(pady=10)
        
        # Create color frames for preview
        color_frame = ttk.LabelFrame(frame, text="Current Colors")
        color_frame.pack(fill="x", pady=10)
        
        color_container = ttk.Frame(color_frame)
        color_container.pack(pady=10)
        
        self.color_frames = []
        for i in range(5):
            color_box = tk.Frame(color_container, width=50, height=50, bg="gray")
            color_box.pack(side="left", padx=5)
            color_box.pack_propagate(False)
            self.color_frames.append(color_box)
        
        # Control buttons
        control_frame = ttk.Frame(frame)
        control_frame.pack(pady=20)
        
        ttk.Button(control_frame, text="Start", command=self.start_application).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Stop", command=self.stop_application).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Capture Now", command=self.capture_wallpaper).pack(side="left", padx=5)
        
        # Harmony options
        harmony_frame = ttk.LabelFrame(frame, text="Color Harmony")
        harmony_frame.pack(fill="x", pady=10)
        
        harmony_options = ["complementary", "analogous", "triadic", "tetradic", "monochromatic"]
        for option in harmony_options:
            ttk.Radiobutton(
                harmony_frame, 
                text=option.capitalize(), 
                value=option, 
                variable=self.harmony_type_var
            ).pack(anchor="w", padx=10)
        
        ttk.Button(harmony_frame, text="Apply Harmony", command=self.apply_harmony).pack(pady=10)
        
        # About button
        ttk.Button(frame, text="About", command=self.show_about).pack(pady=10)
        
        # Add screenshot mode toggle
        screenshot_frame = ttk.LabelFrame(frame, text="Capture Mode")
        screenshot_frame.pack(fill="x", pady=10)
        
        ttk.Checkbutton(
            screenshot_frame,
            text="Use Screenshot Mode (instead of wallpaper)",
            variable=self.screenshot_mode,
            command=self.toggle_screenshot_mode
        ).pack(anchor="w", padx=10, pady=5)
        
        # Add screenshot interval control
        interval_frame = ttk.Frame(screenshot_frame)
        interval_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(interval_frame, text="Update Interval (seconds):").pack(side="left", padx=(0, 10))
        
        self.interval_var = tk.StringVar(value=str(self.config.getint('General', 'update_interval', fallback=60)))
        interval_spinbox = ttk.Spinbox(
            interval_frame,
            from_=1,
            to=300,
            textvariable=self.interval_var,
            width=5
        )
        interval_spinbox.pack(side="left")
        
        # Add a dedicated start capture button
        capture_button_frame = ttk.Frame(frame)
        capture_button_frame.pack(pady=10)
        
        ttk.Button(
            capture_button_frame,
            text="Start Continuous Capture",
            command=self.start_continuous_capture,
            style="Accent.TButton"
        ).pack(side="left", padx=5)
        
        ttk.Button(
            capture_button_frame,
            text="Stop Capture",
            command=self.stop_application
        ).pack(side="left", padx=5)
        
        ttk.Button(
            capture_button_frame,
            text="Force Update Now",
            command=self.force_update
        ).pack(side="left", padx=5)
        
        # Create a custom style for the accent button
        style = ttk.Style()
        style.configure("Accent.TButton", background="#4CAF50", foreground="white")
        
        # Add a preview frame for the captured image
        preview_frame = ttk.LabelFrame(frame, text="Current Capture")
        preview_frame.pack(fill="both", expand=True, pady=10)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg="black")
        self.preview_canvas.pack(fill="both", expand=True, padx=10, pady=10)

        # Add region selection button
        ttk.Button(
            screenshot_frame,
            text="Select Screen Region",
            command=self.select_screen_region
        ).pack(pady=5)

        # Add a checkbox for full screen mode
        self.full_screen_var = tk.BooleanVar(value=not bool(self.config.has_option('WallpaperCapture', 'region')))
        ttk.Checkbutton(
            screenshot_frame,
            text="Capture Full Screen",
            variable=self.full_screen_var,
            command=self.toggle_full_screen
        ).pack(anchor="w", padx=10, pady=5)

    def load_config(self):
        """Load configuration from config.ini file"""
        config = ConfigParser()
        
        if os.path.exists(self.config_path):
            config.read(self.config_path)
        else:
            # Create default configuration
            config['General'] = {
                'update_interval': '60'
            }
            config['ColorAnalyzer'] = {
                'num_colors': '5',
                'resize_width': '100',
                'resize_height': '100',
                'algorithm': 'kmeans',
                'color_harmony': 'true',
                'brightness_threshold': '0.1',
                'saturation_threshold': '0.1'
            }
            config['LightController'] = {
                'type': 'hue',
                'transition_time': '1.0',
                'demo_mode': 'true'
            }
            config['Hue'] = {
                'bridge_ip': ''
            }
            
            # Save default configuration
            with open(self.config_path, 'w') as f:
                config.write(f)
        
        return config

    def update_status(self, status):
        """Update the status label"""
        self.status_label.config(text=status)
        logging.info(status)

    def start_application(self):
        """Start the wallpaper light application"""
        if self.running:
            return
            
        try:
            # Initialize components
            self.wallpaper_capture = WallpaperCapture(self.config)
            self.color_analyzer = ColorAnalyzer(self.config)
            self.light_controller = LightController(self.config)
            
            self.running = True
            self.update_status("Application running")
            
            # Start update thread
            self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
            self.update_thread.start()
            
        except Exception as e:
            logging.error(f"Error starting application: {e}")
            messagebox.showerror("Error", f"Failed to start application: {e}")
            self.update_status(f"Error: {e}")

    def stop_application(self):
        """Stop the wallpaper light application"""
        self.running = False
        
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
            self.update_thread = None
        
        self.update_status("Application stopped")

    def update_loop(self):
        """Main update loop for the application"""
        update_interval = self.config.getint('General', 'update_interval', fallback=2)
        last_update_time = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Only update if enough time has passed
                if current_time - last_update_time >= update_interval:
                    self.update_status("Capturing image...")
                    
                    # Capture wallpaper or screenshot
                    self.wallpaper_image = self.wallpaper_capture.capture()
                    
                    # Schedule UI update on main thread
                    self.root.after(0, self.update_preview)
                    
                    self.update_status("Analyzing colors...")
                    # Analyze colors
                    self.current_colors = self.color_analyzer.analyze(self.wallpaper_image)
                    
                    # Update color preview on main thread
                    def update_colors():
                        for i, color in enumerate(self.current_colors):
                            if i < len(self.color_frames):
                                hex_color = rgb_to_hex(color)
                                self.color_frames[i].config(bg=hex_color)
                    
                    self.root.after(0, update_colors)
                    
                    # Control lights
                    self.light_controller.set_colors(self.current_colors)
                    
                    self.update_status("Colors updated")
                    
                    # Update last update time
                    last_update_time = current_time
                
                # Sleep a short time to prevent CPU hogging
                time.sleep(0.1)
                    
            except Exception as e:
                logging.error(f"Error in update loop: {e}")
                self.update_status(f"Error: {e}")
                time.sleep(1)  # Shorter recovery time

    def apply_custom_colors(self):
        """Apply custom colors to the lights"""
        if not self.light_controller:
            messagebox.showinfo("Application Not Running", "Please start the application first")
            return
            
        try:
            # Apply the colors to the lights
            self.light_controller.set_colors(self.current_colors)
            messagebox.showinfo("Colors Applied", "Custom colors have been applied to the lights")
            
        except Exception as e:
            logging.error(f"Error applying custom colors: {e}")
            messagebox.showerror("Error", f"Failed to apply custom colors: {e}")
    
    def capture_wallpaper(self):
        """Capture the current wallpaper and analyze colors"""
        if not self.wallpaper_capture or not self.color_analyzer:
            try:
                self.wallpaper_capture = WallpaperCapture(self.config)
                self.color_analyzer = ColorAnalyzer(self.config)
            except Exception as e:
                logging.error(f"Error initializing components: {e}")
                messagebox.showerror("Error", f"Failed to initialize components: {e}")
                return
        
        try:
            # Capture wallpaper
            self.wallpaper_image = self.wallpaper_capture.capture()
            
            # Analyze colors
            self.current_colors = self.color_analyzer.analyze(self.wallpaper_image)
            
            messagebox.showinfo("Wallpaper Captured", "Wallpaper has been captured and colors analyzed")
            
        except Exception as e:
            logging.error(f"Error capturing wallpaper: {e}")
            messagebox.showerror("Error", f"Failed to capture wallpaper: {e}")
    
    def apply_harmony(self):
        """Apply color harmony to the current colors"""
        if not self.current_colors:
            messagebox.showinfo("No Colors", "Please capture wallpaper first to get colors")
            return
            
        try:
            # Convert to HSV for easier manipulation
            hsv_colors = [colorsys.rgb_to_hsv(r/255, g/255, b/255) for r, g, b in self.current_colors]
            
            # Get base color
            base_h, base_s, base_v = hsv_colors[0]
            harmony_type = self.harmony_type_var.get()
            
            # Apply harmony
            if harmony_type == "complementary":
                # Add complementary color (opposite on color wheel)
                complement_h = (base_h + 0.5) % 1.0
                harmonized_hsv = [(base_h, base_s, base_v), (complement_h, base_s, base_v)]
                
                # Add some variations
                for i in range(len(self.current_colors) - 2):
                    idx = i % 2
                    h_offset = (i + 1) * 0.05
                    if idx == 0:
                        h = (base_h + h_offset) % 1.0
                    else:
                        h = (complement_h + h_offset) % 1.0
                    harmonized_hsv.append((h, base_s, base_v))
                    
            elif harmony_type == "analogous":
                # Add colors adjacent on the color wheel
                harmonized_hsv = [(base_h, base_s, base_v)]
                for i in range(1, len(self.current_colors)):
                    h_offset = (i * 0.05) % 0.3
                    h = (base_h + h_offset) % 1.0
                    harmonized_hsv.append((h, base_s, base_v))
                    
            elif harmony_type == "triadic":
                # Add colors at 120° intervals
                harmonized_hsv = [(base_h, base_s, base_v)]
                for i in range(1, min(3, len(self.current_colors))):
                    h = (base_h + i/3) % 1.0
                    harmonized_hsv.append((h, base_s, base_v))
                    
                # Add variations for remaining colors
                for i in range(3, len(self.current_colors)):
                    base_idx = i % 3
                    h_offset = ((i // 3) + 1) * 0.05
                    h = (harmonized_hsv[base_idx][0] + h_offset) % 1.0
                    harmonized_hsv.append((h, base_s, base_v))
                    
            elif harmony_type == "tetradic":
                # Add colors at 90° intervals
                harmonized_hsv = [(base_h, base_s, base_v)]
                for i in range(1, min(4, len(self.current_colors))):
                    h = (base_h + i/4) % 1.0
                    harmonized_hsv.append((h, base_s, base_v))
                    
                # Add variations for remaining colors
                for i in range(4, len(self.current_colors)):
                    base_idx = i % 4
                    h_offset = ((i // 4) + 1) * 0.05
                    h = (harmonized_hsv[base_idx][0] + h_offset) % 1.0
                    harmonized_hsv.append((h, base_s, base_v))
                    
            elif harmony_type == "monochromatic":
                # Keep the same hue but vary saturation and value
                harmonized_hsv = [(base_h, base_s, base_v)]
                for i in range(1, len(self.current_colors)):
                    s_offset = (i * 0.15) % 0.6 - 0.3
                    v_offset = (i * 0.1) % 0.4 - 0.2
                    
                    s = max(0.1, min(1.0, base_s + s_offset))
                    v = max(0.2, min(0.9, base_v + v_offset))
                    
                    harmonized_hsv.append((base_h, s, v))
            
            # Convert back to RGB
            harmonized_rgb = []
            for h, s, v in harmonized_hsv[:len(self.current_colors)]:
                r, g, b = colorsys.hsv_to_rgb(h, s, v)
                harmonized_rgb.append((int(r * 255), int(g * 255), int(b * 255)))
            
            # Update current colors
            self.current_colors = harmonized_rgb
            
            # Update UI
            for i, color in enumerate(self.current_colors):
                if i < len(self.color_preview_frames):
                    hex_color = rgb_to_hex(color)
                    frame, label, _ = self.color_preview_frames[i]
                    frame.config(bg=hex_color)
                    label.config(text=hex_color)
                    
                    # Update color frame in main tab
                    if i < len(self.color_frames):
                        self.color_frames[i].config(bg=hex_color)
            
            messagebox.showinfo("Harmony Applied", f"{harmony_type.capitalize()} harmony has been applied to the colors")
            
        except Exception as e:
            logging.error(f"Error applying harmony: {e}")
            messagebox.showerror("Error", f"Failed to apply harmony: {e}")
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About Wallpaper Light",
            "Wallpaper Light\n\n"
            "A tool to control smart lights based on wallpaper colors\n\n"
            "This application captures your desktop wallpaper, analyzes its colors,\n"
            "and controls connected lights to match the dominant colors."
        )

    def toggle_screenshot_mode(self):
        """Toggle between wallpaper and screenshot mode"""
        use_screenshot = self.screenshot_mode.get()
        self.config.set('WallpaperCapture', 'use_screenshot', str(use_screenshot))
        
        # Save the configuration
        with open(self.config_path, 'w') as f:
            self.config.write(f)
        
        mode_name = "Screenshot" if use_screenshot else "Wallpaper"
        self.update_status(f"Capture mode set to: {mode_name}")
    
    def start_continuous_capture(self):
        """Start continuous screen capture"""
        # Update the interval from the UI
        try:
            interval = int(self.interval_var.get())
            if interval < 1:
                interval = 1
            elif interval > 300:
                interval = 300
                
            self.config.set('General', 'update_interval', str(interval))
            
            # Save the configuration
            with open(self.config_path, 'w') as f:
                self.config.write(f)
                
            self.update_status(f"Update interval set to {interval} seconds")
        except ValueError:
            self.update_status("Invalid interval value, using default")
        
        # Start the application
        self.start_application()
        
        # Update status
        if self.screenshot_mode.get():
            self.update_status("Started continuous screenshot capture")
        else:
            self.update_status("Started wallpaper monitoring")

    def update_preview(self):
        """Update the preview canvas with the current wallpaper/screenshot"""
        if self.wallpaper_image:
            try:
                # Get canvas dimensions
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()
                
                # Skip if canvas is not yet properly sized
                if canvas_width <= 1 or canvas_height <= 1:
                    return
                    
                # Calculate aspect ratio
                img_width, img_height = self.wallpaper_image.size
                aspect_ratio = img_width / img_height
                
                # Calculate new dimensions
                if canvas_width / canvas_height > aspect_ratio:
                    # Canvas is wider than image
                    new_height = canvas_height
                    new_width = int(new_height * aspect_ratio)
                else:
                    # Canvas is taller than image
                    new_width = canvas_width
                    new_height = int(new_width / aspect_ratio)
                
                # Resize image
                resized_img = self.wallpaper_image.resize((new_width, new_height))
                self.tk_image = ImageTk.PhotoImage(resized_img)
                
                # Clear canvas and draw image
                self.preview_canvas.delete("all")
                self.preview_canvas.create_image(
                    canvas_width // 2, canvas_height // 2,
                    image=self.tk_image, anchor="center"
                )
            except Exception as e:
                logging.error(f"Error updating preview: {e}")

    def update_ui(self):
        """Periodic UI update function"""
        # Update preview if we have an image
        if self.wallpaper_image:
            self.update_preview()
        
        # Schedule next update
        self.root.after(1000, self.update_ui)

    def force_update(self):
        """Force an immediate update"""
        if not self.running:
            messagebox.showinfo("Not Running", "Please start the application first")
            return
        
        # Run capture and update in a separate thread to avoid freezing UI
        threading.Thread(target=self.do_force_update, daemon=True).start()

    def do_force_update(self):
        """Perform the forced update"""
        try:
            self.update_status("Forcing update...")
            
            # Capture wallpaper or screenshot
            self.wallpaper_image = self.wallpaper_capture.capture()
            
            # Schedule UI update on main thread
            self.root.after(0, self.update_preview)
            
            # Analyze colors
            self.current_colors = self.color_analyzer.analyze(self.wallpaper_image)
            
            # Update color preview on main thread
            def update_colors():
                for i, color in enumerate(self.current_colors):
                    if i < len(self.color_frames):
                        hex_color = rgb_to_hex(color)
                        self.color_frames[i].config(bg=hex_color)
            
            self.root.after(0, update_colors)
            
            # Control lights
            self.light_controller.set_colors(self.current_colors)
            
            self.update_status("Forced update completed")
            
        except Exception as e:
            logging.error(f"Error in forced update: {e}")
            self.update_status(f"Error: {e}")

    def select_screen_region(self):
        """Open the screen region selector"""
        # Initialize wallpaper capture if needed
        if not self.wallpaper_capture:
            try:
                self.wallpaper_capture = WallpaperCapture(self.config)
            except Exception as e:
                logging.error(f"Error initializing wallpaper capture: {e}")
                messagebox.showerror("Error", f"Failed to initialize wallpaper capture: {e}")
                return
        
        try:
            # Capture a full screenshot for selection
            original_region = self.wallpaper_capture.capture_region
            self.wallpaper_capture.capture_region = None
            screenshot = self.wallpaper_capture.capture_screenshot()
            
            # Open the region selector
            selector = ScreenRegionSelector(self.root)
            region = selector.open_selector(screenshot)
            
            if region:
                # Set the new region
                self.wallpaper_capture.set_capture_region(region)
                
                # Update the full screen checkbox
                self.full_screen_var.set(False)
                
                # Save the configuration
                with open(self.config_path, 'w') as f:
                    self.config.write(f)
                    
                # Capture a test screenshot with the new region
                self.wallpaper_image = self.wallpaper_capture.capture()
                self.update_preview()
                
                self.update_status(f"Screen region selected: {region}")
            else:
                # Restore the original region
                self.wallpaper_capture.capture_region = original_region
                self.update_status("Region selection canceled")
                
        except Exception as e:
            logging.error(f"Error selecting screen region: {e}")
            messagebox.showerror("Error", f"Failed to select screen region: {e}")

    def toggle_full_screen(self):
        """Toggle between full screen and region capture"""
        if not self.wallpaper_capture:
            try:
                self.wallpaper_capture = WallpaperCapture(self.config)
            except Exception as e:
                logging.error(f"Error initializing wallpaper capture: {e}")
                messagebox.showerror("Error", f"Failed to initialize wallpaper capture: {e}")
                return
        
        if self.full_screen_var.get():
            # Switch to full screen
            self.wallpaper_capture.set_capture_region(None)
            
            # Save the configuration
            with open(self.config_path, 'w') as f:
                self.config.write(f)
            
            self.update_status("Switched to full screen capture")
        else:
            # Prompt to select a region
            self.select_screen_region()

def main():
    """Main function to run the GUI"""
    root = tk.Tk()
    app = WallpaperLightGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 
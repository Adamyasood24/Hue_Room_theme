"""
Module for controlling smart lights
"""
import logging
import time
import colorsys


class LightController:
    """Class to control smart lights"""
    
    def __init__(self, config):
        """
        Initialize the light controller
        
        Args:
            config: ConfigParser object with application configuration
        """
        self.config = config
        self.light_type = config.get('LightController', 'type', fallback='hue')
        self.transition_time = config.getfloat('LightController', 'transition_time', fallback=1.0)
        self.demo_mode = config.getboolean('LightController', 'demo_mode', fallback=False)
        
        logging.info(f"Initializing light controller for {self.light_type} lights")
        
        # Use demo mode if configured or if real lights fail to initialize
        if self.demo_mode:
            logging.info("Running in demo mode - no actual lights will be controlled")
            self.lights = ["Demo Light 1", "Demo Light 2", "Demo Light 3"]
            return
            
        # Initialize the appropriate light controller
        try:
            if self.light_type.lower() == 'hue':
                self._init_hue()
            elif self.light_type.lower() == 'lifx':
                self._init_lifx()
            elif self.light_type.lower() == 'yeelight':
                self._init_yeelight()
            else:
                logging.warning(f"Unsupported light type: {self.light_type}")
                self.lights = []
                
            # If no lights were found, fall back to demo mode
            if not self.lights:
                logging.warning("No lights found, falling back to demo mode")
                self.demo_mode = True
                self.lights = ["Demo Light 1", "Demo Light 2", "Demo Light 3"]
                
        except Exception as e:
            logging.error(f"Failed to initialize lights: {e}")
            logging.warning("Falling back to demo mode")
            self.demo_mode = True
            self.lights = ["Demo Light 1", "Demo Light 2", "Demo Light 3"]
    
    def _init_hue(self):
        """Initialize Philips Hue controller"""
        try:
            from phue import Bridge
            
            bridge_ip = self.config.get('Hue', 'bridge_ip', fallback=None)
            if not bridge_ip:
                logging.error("Hue bridge IP not specified in config")
                return
            
            self.bridge = Bridge(bridge_ip)
            
            # Try to connect to the bridge
            try:
                self.bridge.connect()
                self.lights = self.bridge.lights
                logging.info(f"Connected to Hue bridge at {bridge_ip} with {len(self.lights)} lights")
            except Exception as e:
                logging.error(f"Failed to connect to Hue bridge: {e}")
                self.lights = []
                
        except ImportError:
            logging.error("phue package not installed. Install with: pip install phue")
            self.lights = []
    
    def _init_lifx(self):
        """Initialize LIFX controller"""
        try:
            import lifxlan
            
            self.lifx = lifxlan.LifxLAN()
            self.lights = self.lifx.get_lights()
            logging.info(f"Discovered {len(self.lights)} LIFX lights")
            
        except ImportError:
            logging.error("lifxlan package not installed. Install with: pip install lifxlan")
            self.lights = []
    
    def _init_yeelight(self):
        """Initialize Yeelight controller"""
        try:
            from yeelight import discover_bulbs, Bulb
            
            discovered_bulbs = discover_bulbs()
            self.lights = [Bulb(bulb["ip"]) for bulb in discovered_bulbs]
            logging.info(f"Discovered {len(self.lights)} Yeelight bulbs")
            
        except ImportError:
            logging.error("yeelight package not installed. Install with: pip install yeelight")
            self.lights = []
    
    def set_colors(self, colors):
        """
        Set lights to the given colors
        
        Args:
            colors: List of (R, G, B) color tuples
        """
        if not self.lights:
            logging.warning("No lights available to control")
            return
        
        if not colors:
            logging.warning("No colors provided to set lights")
            return
        
        # Distribute colors among lights
        for i, light in enumerate(self.lights):
            # Use modulo to cycle through colors if we have more lights than colors
            color = colors[i % len(colors)]
            self._set_light_color(light, color, i)
    
    def _set_light_color(self, light, color, index):
        """
        Set a specific light to a color
        
        Args:
            light: Light object
            color: (R, G, B) color tuple
            index: Light index for logging
        """
        r, g, b = color
        
        # In demo mode, just log the color change
        if self.demo_mode:
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            logging.info(f"Demo mode: Set light {index} ({light}) to color {hex_color}")
            return
            
        try:
            if self.light_type.lower() == 'hue':
                # Convert RGB to Hue color format
                from phue import rgb_to_xy
                xy = rgb_to_xy(r, g, b)
                light.xy = xy
                light.brightness = 254  # Max brightness
                logging.debug(f"Set Hue light {index} to color {color}")
                
            elif self.light_type.lower() == 'lifx':
                # LIFX uses HSBK (Hue, Saturation, Brightness, Kelvin)
                import colorsys
                h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                # Convert to LIFX ranges
                hue = int(h * 65535)
                saturation = int(s * 65535)
                brightness = int(v * 65535)
                light.set_color([hue, saturation, brightness, 3500])
                logging.debug(f"Set LIFX light {index} to color {color}")
                
            elif self.light_type.lower() == 'yeelight':
                light.set_rgb(r, g, b)
                logging.debug(f"Set Yeelight {index} to color {color}")
                
        except Exception as e:
            logging.error(f"Failed to set light {index} to color {color}: {e}") 
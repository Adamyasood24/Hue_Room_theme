"""
Module for analyzing colors in images using AI-based approaches
"""
import logging
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import colorsys


class ColorAnalyzer:
    """Class to analyze colors in images using AI techniques"""
    
    def __init__(self, config):
        """
        Initialize the color analyzer
        
        Args:
            config: ConfigParser object with application configuration
        """
        self.config = config
        self.num_colors = config.getint('ColorAnalyzer', 'num_colors', fallback=5)
        self.resize_width = config.getint('ColorAnalyzer', 'resize_width', fallback=100)
        self.resize_height = config.getint('ColorAnalyzer', 'resize_height', fallback=100)
        self.algorithm = config.get('ColorAnalyzer', 'algorithm', fallback='kmeans')
        self.color_harmony = config.getboolean('ColorAnalyzer', 'color_harmony', fallback=True)
        self.brightness_threshold = config.getfloat('ColorAnalyzer', 'brightness_threshold', fallback=0.1)
        self.saturation_threshold = config.getfloat('ColorAnalyzer', 'saturation_threshold', fallback=0.1)
        
        logging.info(f"Initializing AI-based color analyzer to extract {self.num_colors} colors using {self.algorithm}")
    
    def analyze(self, image):
        """
        Analyze the image and extract dominant colors using AI techniques
        
        Args:
            image: PIL.Image object to analyze
            
        Returns:
            list: List of dominant colors as (R, G, B) tuples
        """
        # Resize image for faster processing
        resized_image = image.resize((self.resize_width, self.resize_height))
        
        # Convert to RGB if needed
        if resized_image.mode != 'RGB':
            resized_image = resized_image.convert('RGB')
        
        # Convert to numpy array
        np_image = np.array(resized_image)
        pixels = np_image.reshape(-1, 3)
        
        # Filter out very dark or very light pixels
        filtered_pixels = self._filter_pixels(pixels)
        
        # If too many pixels were filtered, use original pixels
        if len(filtered_pixels) < (self.resize_width * self.resize_height * 0.1):
            logging.warning("Too many pixels filtered out, using original pixels")
            filtered_pixels = pixels
        
        # Choose algorithm based on configuration
        if self.algorithm.lower() == 'kmeans':
            colors = self._kmeans_clustering(filtered_pixels)
        elif self.algorithm.lower() == 'quantile':
            colors = self._quantile_based(filtered_pixels)
        elif self.algorithm.lower() == 'histogram':
            colors = self._histogram_based(np_image)
        else:
            logging.warning(f"Unknown algorithm: {self.algorithm}, falling back to K-means")
            colors = self._kmeans_clustering(filtered_pixels)
        
        # Apply color harmony if enabled
        if self.color_harmony:
            colors = self._apply_color_harmony(colors)
        
        logging.debug(f"Extracted colors: {colors}")
        return colors
    
    def _filter_pixels(self, pixels):
        """
        Filter out pixels that are too dark or too light
        
        Args:
            pixels: Numpy array of pixels
            
        Returns:
            Numpy array of filtered pixels
        """
        # Convert RGB to HSV for better filtering
        hsv_pixels = np.array([colorsys.rgb_to_hsv(r/255, g/255, b/255) for r, g, b in pixels])
        
        # Filter based on brightness (V in HSV) and saturation (S in HSV)
        mask = (hsv_pixels[:, 2] > self.brightness_threshold) & \
               (hsv_pixels[:, 2] < (1 - self.brightness_threshold)) & \
               (hsv_pixels[:, 1] > self.saturation_threshold)
        
        return pixels[mask]
    
    def _kmeans_clustering(self, pixels):
        """
        Use K-means clustering to find dominant colors
        
        Args:
            pixels: Numpy array of pixels
            
        Returns:
            list: List of dominant colors as (R, G, B) tuples
        """
        kmeans = KMeans(n_clusters=self.num_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        # Get the colors
        colors = kmeans.cluster_centers_.astype(int)
        
        # Get cluster sizes to sort colors by dominance
        labels = kmeans.labels_
        counts = np.bincount(labels)
        
        # Sort colors by cluster size (most dominant first)
        sorted_indices = np.argsort(counts)[::-1]
        sorted_colors = colors[sorted_indices]
        
        # Convert to list of tuples
        return [tuple(color) for color in sorted_colors]
    
    def _quantile_based(self, pixels):
        """
        Use quantile-based approach to find representative colors
        
        Args:
            pixels: Numpy array of pixels
            
        Returns:
            list: List of dominant colors as (R, G, B) tuples
        """
        # Calculate quantiles for each channel
        colors = []
        for i in range(self.num_colors):
            quantile = (i + 1) / (self.num_colors + 1)
            r = int(np.quantile(pixels[:, 0], quantile))
            g = int(np.quantile(pixels[:, 1], quantile))
            b = int(np.quantile(pixels[:, 2], quantile))
            colors.append((r, g, b))
        
        return colors
    
    def _histogram_based(self, image_array):
        """
        Use color histograms to find dominant colors
        
        Args:
            image_array: Numpy array of the image
            
        Returns:
            list: List of dominant colors as (R, G, B) tuples
        """
        # Reduce color space to make histogram manageable
        bins = 25
        
        # Create 3D histogram
        hist, edges = np.histogramdd(
            image_array.reshape(-1, 3),
            bins=[bins, bins, bins],
            range=[(0, 255), (0, 255), (0, 255)]
        )
        
        # Find the centers of the bins
        r_centers = (edges[0][:-1] + edges[0][1:]) / 2
        g_centers = (edges[1][:-1] + edges[1][1:]) / 2
        b_centers = (edges[2][:-1] + edges[2][1:]) / 2
        
        # Flatten the histogram and get the indices of the top N bins
        indices = np.argsort(hist.flatten())[-self.num_colors:]
        
        # Convert flat indices to 3D indices
        colors = []
        for idx in indices:
            r_idx, g_idx, b_idx = np.unravel_index(idx, (bins, bins, bins))
            colors.append((int(r_centers[r_idx]), int(g_centers[g_idx]), int(b_centers[b_idx])))
        
        return colors
    
    def _apply_color_harmony(self, colors):
        """
        Apply color harmony rules to make colors more aesthetically pleasing
        
        Args:
            colors: List of (R, G, B) color tuples
            
        Returns:
            list: List of harmonized colors as (R, G, B) tuples
        """
        if len(colors) <= 1:
            return colors
        
        # Convert to HSV for easier manipulation
        hsv_colors = [colorsys.rgb_to_hsv(r/255, g/255, b/255) for r, g, b in colors]
        
        # Choose a harmony model based on the first color
        base_hue = hsv_colors[0][0]
        harmony_model = self._select_harmony_model(base_hue)
        
        # Apply the harmony model
        harmonized_hsv = self._apply_harmony_model(hsv_colors, harmony_model)
        
        # Convert back to RGB
        harmonized_rgb = []
        for h, s, v in harmonized_hsv:
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            harmonized_rgb.append((int(r * 255), int(g * 255), int(b * 255)))
        
        return harmonized_rgb
    
    def _select_harmony_model(self, base_hue):
        """
        Select a color harmony model based on the base hue
        
        Args:
            base_hue: Base hue value (0-1)
            
        Returns:
            str: Harmony model name
        """
        # Randomly select a harmony model with some weighting
        import random
        models = ['complementary', 'analogous', 'triadic', 'tetradic', 'monochromatic']
        weights = [0.2, 0.3, 0.2, 0.1, 0.2]
        
        return random.choices(models, weights=weights, k=1)[0]
    
    def _apply_harmony_model(self, hsv_colors, model):
        """
        Apply a specific harmony model to the colors
        
        Args:
            hsv_colors: List of (H, S, V) color tuples
            model: Harmony model name
            
        Returns:
            list: List of harmonized (H, S, V) color tuples
        """
        base_h, base_s, base_v = hsv_colors[0]
        result = [hsv_colors[0]]  # Keep the first color
        
        if model == 'complementary':
            # Add complementary color (opposite on color wheel)
            complement_h = (base_h + 0.5) % 1.0
            result.append((complement_h, base_s, base_v))
            
            # Add some variations
            for i in range(len(hsv_colors) - 2):
                idx = i % 2
                h_offset = (i + 1) * 0.05
                if idx == 0:
                    h = (base_h + h_offset) % 1.0
                else:
                    h = (complement_h + h_offset) % 1.0
                result.append((h, base_s, base_v))
                
        elif model == 'analogous':
            # Add colors adjacent on the color wheel
            for i in range(1, len(hsv_colors)):
                h_offset = (i * 0.05) % 0.3
                h = (base_h + h_offset) % 1.0
                result.append((h, base_s, base_v))
                
        elif model == 'triadic':
            # Add colors at 120° intervals
            for i in range(1, min(3, len(hsv_colors))):
                h = (base_h + i/3) % 1.0
                result.append((h, base_s, base_v))
                
            # Add variations for remaining colors
            for i in range(3, len(hsv_colors)):
                base_idx = i % 3
                h_offset = ((i // 3) + 1) * 0.05
                h = (result[base_idx][0] + h_offset) % 1.0
                result.append((h, base_s, base_v))
                
        elif model == 'tetradic':
            # Add colors at 90° intervals
            for i in range(1, min(4, len(hsv_colors))):
                h = (base_h + i/4) % 1.0
                result.append((h, base_s, base_v))
                
            # Add variations for remaining colors
            for i in range(4, len(hsv_colors)):
                base_idx = i % 4
                h_offset = ((i // 4) + 1) * 0.05
                h = (result[base_idx][0] + h_offset) % 1.0
                result.append((h, base_s, base_v))
                
        elif model == 'monochromatic':
            # Keep the same hue but vary saturation and value
            for i in range(1, len(hsv_colors)):
                s_offset = (i * 0.15) % 0.6 - 0.3
                v_offset = (i * 0.1) % 0.4 - 0.2
                
                s = max(0.1, min(1.0, base_s + s_offset))
                v = max(0.2, min(0.9, base_v + v_offset))
                
                result.append((base_h, s, v))
        
        # Ensure we return the right number of colors
        return result[:len(hsv_colors)] 
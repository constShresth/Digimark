import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import re
from pdf2image import convert_from_path
import tempfile

class OCREngine:
    def __init__(self, languages='eng'):
        """
        Initialize OCR Engine
        
        Parameters:
        languages (str): Languages to use for OCR (default: 'eng')
                        Use '+' to separate multiple languages (e.g., 'eng+hin+guj')
        """
        self.languages = languages
        
        # Set Tesseract path if needed (uncomment and modify for your system)
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    def preprocess_image(self, image):
        """Preprocess image for better OCR results"""
        # Convert to grayscale if it's a color image
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Noise removal
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        # Dilation to make text more prominent
        kernel = np.ones((1, 1), np.uint8)
        dilated = cv2.dilate(opening, kernel, iterations=1)
        
        return dilated
    
    def load_file(self, filepath):
        """Load image or PDF file and return list of images"""
        if filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff')):
            return [cv2.imread(filepath)]
        elif filepath.lower().endswith('.pdf'):
            # Convert PDF to images
            return [np.array(img) for img in convert_from_path(filepath)]
        else:
            raise ValueError("Unsupported file format")
    
    def extract_text(self, image):
        """Extract text from image using OCR"""
        # Configure tesseract for handwritten text
        custom_config = f'--oem 3 --psm 6 -l {self.languages}'
        
        # Extract text using OCR
        text = pytesseract.image_to_string(image, config=custom_config)
        
        return text.strip()
    
    def detect_answer_regions(self, image, num_regions=5):
        """
        Detect answer regions in the image
        
        Parameters:
        image (numpy.ndarray): Input image
        num_regions (int): Number of regions to detect
        
        Returns:
        list: List of region dictionaries with id, image, and coordinates
        """
        height, width = image.shape[:2]
        region_height = height // num_regions
        
        regions = []
        for i in range(num_regions):
            y_start = i * region_height
            y_end = (i + 1) * region_height
            region = image[y_start:y_end, 0:width]
            regions.append({
                'id': f'q{i+1}',
                'image': region,
                'coordinates': (0, y_start, width, y_end)
            })
        
        return regions
    
    def process_answer_sheet(self, filepath, num_regions=5):
        """
        Process a complete answer sheet and extract text from all regions
        
        Parameters:
        filepath (str): Path to the answer sheet image
        num_regions (int): Number of regions to detect
        
        Returns:
        dict: Dictionary mapping question IDs to extracted text
        """
        # Load images from file
        images = self.load_file(filepath)
        
        results = {}
        
        for page_num, image in enumerate(images):
            # Preprocess the image
            preprocessed = self.preprocess_image(image)
            
            # Detect answer regions
            regions = self.detect_answer_regions(preprocessed, num_regions)
            
            # Extract text from each region
            for region in regions:
                region_id = region['id']
                region_image = region['image']
                
                # Extract text
                text = self.extract_text(region_image)
                
                # Store result
                results[region_id] = text
        
        return results

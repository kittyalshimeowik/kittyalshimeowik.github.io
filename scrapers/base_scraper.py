import os
import json
from abc import ABC, abstractmethod
from datetime import datetime

class BaseScraper(ABC):
    """
    Abstract Base Class that defines the standard interface for
    all real estate scrapers in the Armenia project.
    """

    def __init__(self, output_subdir, metadata_subdir=None):
        # Anchor paths relative to the project root (.. relative to 'scrapers' directory)
        self.PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        
        # Define output and metadata directory paths
        self.OUTPUT_DIR = os.path.join(self.PROJECT_ROOT, "scrapers", output_subdir)
        if metadata_subdir:
            self.METADATA_DIR = os.path.join(self.PROJECT_ROOT, "scrapers", metadata_subdir)
        else:
            self.METADATA_DIR = None

        # Ensure output directories exist
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        if self.METADATA_DIR:
            os.makedirs(self.METADATA_DIR, exist_ok=True)

    @abstractmethod
    def run(self, **kwargs):
        """
        Main execution logic for the scraper. Must be implemented by subclasses.
        kwargs can include time_limit, dynamic_runtime_min, etc.
        """
        pass

    def load_existing_dataset(self, filename):
        """Safely loads and returns existing data from an output JSON file."""
        file_path = os.path.join(self.OUTPUT_DIR, filename)
        if not os.path.exists(file_path):
            return [], set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data, set(p.get("url") for p in data if p.get("url"))
        except Exception:
            return [], set()

    def save_final_results(self, filename, all_posts):
        """Saves combined and deduplicated results back to the output folder."""
        file_path = os.path.join(self.OUTPUT_DIR, filename)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(all_posts, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving results to {file_path}: {e}")

    # --- Standard Extraction Utilities used by multiple sites ---
    @staticmethod
    def normalize_price_amount(raw_str):
        if not raw_str: return None
        cleaned = "".join([c for c in raw_str if c.isdigit()])
        try: return int(cleaned)
        except ValueError: return None

    @staticmethod
    def sanitize_area_size(raw_str):
        if not raw_str: return None
        # Remove units, spaces, dots/commas if used as separators
        cleaned = re.sub(r'[^\d.]', '', raw_str.strip())
        try: return float(cleaned)
        except ValueError: return None
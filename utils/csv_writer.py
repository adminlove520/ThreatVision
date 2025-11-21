import csv
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .logger import setup_logger

logger = setup_logger(__name__)

class CSVWriter:
    def __init__(self, filepath):
        self.filepath = filepath
        self.ensure_directory()

    def ensure_directory(self):
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def write_header(self, headers):
        """Write CSV header if file is empty or new"""
        try:
            file_exists = os.path.exists(self.filepath) and os.path.getsize(self.filepath) > 0
            if not file_exists:
                with open(self.filepath, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
        except Exception as e:
            logger.error(f"Error writing CSV header: {e}")

    def append_row(self, row_data):
        """Append a single row of data"""
        try:
            with open(self.filepath, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(row_data)
        except Exception as e:
            logger.error(f"Error appending to CSV: {e}")

    def append_rows(self, rows_data):
        """Append multiple rows"""
        try:
            with open(self.filepath, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(rows_data)
        except Exception as e:
            logger.error(f"Error appending rows to CSV: {e}")

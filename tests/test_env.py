"""
Environment Verification Test Script for SU-DRISHTI.
Tests import of all required packages, checks OpenCV build, and verifies torch/YOLO runtime.
"""
import sys
import os

def test_environment():
    print(f"Python Executable: {sys.executable}")
    print(f"Python Version: {sys.version}")
    
    # 1. Standard library modules
    import sqlite3
    import datetime
    import pathlib
    print(f"[OK] Standard modules (sqlite3, datetime, pathlib) loaded successfully.")
    
    # 2. NumPy
    import numpy as np
    print(f"[OK] NumPy version: {np.__version__}")
    
    # 3. Pandas
    import pandas as pd
    print(f"[OK] Pandas version: {pd.__version__}")
    
    # 4. Streamlit
    import streamlit as st
    print(f"[OK] Streamlit version: {st.__version__}")
    
    # 5. OpenCV
    import cv2
    print(f"[OK] OpenCV version: {cv2.__version__}")
    
    # 6. Ultralytics / Torch
    import torch
    print(f"[OK] PyTorch version: {torch.__version__} (CUDA available: {torch.cuda.is_available()})")
    import ultralytics
    print(f"[OK] Ultralytics YOLO version: {ultralytics.__version__}")
    
    print("\n--- ALL CORE DEPENDENCIES VERIFIED SUCCESSFULLY ---")

if __name__ == "__main__":
    test_environment()

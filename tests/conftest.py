import os

# Test modules import cv2 before qrguard, so set the decode limit before any of them load,
# exactly as qrguard/__init__.py does for the service. test_decode_limit_in_a_fresh_process
# checks the package's own setting in the import order the service uses.
os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(50_000_000))

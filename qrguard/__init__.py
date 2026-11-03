import os

__version__ = "1.0.1"

# OpenCV reads this once, when it is first imported, and every module here imports it through this
# package. A photo may claim any size: refuse to decode more than 50 megapixels (a 12 MP phone photo
# is well inside) instead of allocating gigabytes for a crafted file.
os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(50_000_000))

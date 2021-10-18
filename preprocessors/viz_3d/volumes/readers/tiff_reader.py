from pathlib import Path
import vtk
from . import image_reader


# tiff reader
class TiffReader (image_reader.ImageReader):
    TYPE_NAMES = ['image/tiff']
    MIN_FILES = 100

    def __init__(self, starting_directory):
        image_reader.ImageReader.__init__(self, starting_directory)

    def vtk_array_to_vti_reader(self, array):
        reader = vtk.vtkTIFFReader()
        buf = bytearray(15000000000)
        reader.SetMemoryBuffer(buf)
        reader.SetFileNames(array)
        reader.SetFileDimensionality(2)
        reader.SetFileNameSliceSpacing(1)
        reader.SetDataSpacing(1, 1, 1)
        return(reader)

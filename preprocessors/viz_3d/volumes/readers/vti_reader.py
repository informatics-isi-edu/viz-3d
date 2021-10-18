from pathlib import Path
import vtk
from . import image_reader


class VTIReader (image_reader.ImageReader):
    MIN_FILES = 1

    def __init__(self, starting_directory):
        image_reader.ImageReader.__init__(self, starting_directory)

    def vtk_array_to_vti_reader(self, array):
        reader = vtk.vtkXMLImageDataReader()
        reader.SetFileName(array.GetValue(0))
        return(reader)

    def file_type_matches(self, file):
        # this should be an XML file containing a VTKFile object, but
        # just go by filename for now
        return(file.suffix == '.vti')

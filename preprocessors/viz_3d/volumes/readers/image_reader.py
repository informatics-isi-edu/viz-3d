from pathlib import Path
import vtk
import filetype


# base class for image readers
class ImageReader:
    TYPE_NAMES = []
    MIN_FILES = 1

    def __init__(self, starting_directory):
        self.toplevel_directory = Path(starting_directory)
        self.image_directory = self.find_directory()

    def get_vti_reader(self):
        return self.vtk_array_to_vti_reader(
            self.get_vtk_array())

    # is this file a type I know how to process?
    @classmethod
    def file_type_matches(cls, filename):
        file_type = filetype.guess_mime(filename)
        return (file_type is not None and file_type in cls.TYPE_NAMES)

    # return a Path object for the directory under self.toplevel that contains
    # the actual image file(s)
    def find_directory(self, dir=None):
        if dir is None:
            dir = self.toplevel_directory
        count = 0
        for child in dir.iterdir():
            if child.is_file() and self.file_type_matches(child):
                count = count + 1
                if count >= self.MIN_FILES:
                    return(dir)
            elif child.is_dir():
                found = self.find_directory(dir=child)
                if found is not None:
                    return found
        return None

    # list the image file names
    def get_vtk_array(self):
        if self.image_directory is None:
            return None
        a = vtk.vtkStringArray()
        for child in self.image_directory.iterdir():
            if child.is_file() and self.file_type_matches(child):
                a.InsertNextValue(child.as_posix())
        return(a)

    def vtk_array_to_vti_reader(self, array):
        raise NotImplementedError()

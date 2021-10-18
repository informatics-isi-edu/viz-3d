from . import tiff_reader
from . import vti_reader

__all__ = ['new_image_reader']


def new_image_reader(starting_directory, type_hint=None):
    IMAGE_READERS = {
        tiff_reader.TiffReader: ["image/tiff", "tiff"],
        vti_reader.VTIReader: []
    }

    for reader in IMAGE_READERS.keys():
        new_instance = reader(starting_directory)
        if new_instance.image_directory is not None:
            return(new_instance)

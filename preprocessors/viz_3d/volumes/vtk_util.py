import vtk
from urllib import request, parse
from pathlib import Path
from pyunpack import Archive, PatoolError
from zipfile import BadZipFile
import sys
import re
import os
from ctypes import *
import logging
import subprocess
import shutil
from . import readers


class VtkUtil:

    # scratch_directory is a directory with lots of space for scratch files
    # host is just used to expand relative urls
    def __init__(self, host, scratch_directory):
        self.host = host
        self.base_scratch_directory = Path(scratch_directory)

    # generates a filename of the form
    #   /scratch_dir/image_id/filename[_downsample].vti
    def image_file_name(self, image_id, filename, downsample=None):
        filename = Path(filename).stem
        if downsample:
            filename = filename + '_' + str(downsample)
        return((self.scratch_image_directory(image_id) / filename)
               .with_suffix('.vti').as_posix())

    def scratch_image_directory(self, image_id):
        return self.base_scratch_directory / image_id

    def clean_scratch_files(self, image_id):
        shutil.rmtree(
            self.scratch_image_directory(image_id).as_posix(), ignore_errors=True)

    # write a vtk reader object to a set of parallelized vti files
    @classmethod
    def write_pvti_from_reader(cls, reader, outfilename, number_of_pieces):
        if number_of_pieces < 1:
            number_of_pieces = os.cpu_count()
        writer = vtk.vtkXMLPImageDataWriter()
        writer.SetFileName(outfilename)
        writer.SetNumberOfPieces(number_of_pieces)
        writer.SetStartPiece(0)
        writer.SetEndPiece(number_of_pieces-1)
        writer.SetInputConnection(reader.GetOutputPort())
        writer.Update()
        writer.Write()

    # write a vtk reader object to a vti file
    @classmethod
    def write_vti_from_reader(cls, reader, outfile):
        writer = vtk.vtkXMLImageDataWriter()
        writer.SetFileName(outfile)
        writer.SetInputConnection(reader.GetOutputPort())
#        writer.Update()
        writer.Write()

    @classmethod
    def vti_file_to_reader(cls, filename):
        reader = vtk.vtkXMLImageDataReader()
        reader.SetFileName(filename)
        return(reader)

    @classmethod
    def vti_downsample(cls, reader, fraction):
        if fraction == 1.0:
            return(reader)
        if fraction <= 0 or fraction > 1:
            raise ValueError('fraction should be between 0 and 1')
        resizer = vtk.vtkImageResize()
        resizer.SetInputConnection(reader.GetOutputPort())
        resizer.SetResizeMethod(resizer.MAGNIFICATION_FACTORS)
        resizer.SetMagnificationFactors(fraction, fraction, fraction)
        return(resizer)

    @classmethod
    def downsample_vti_file(cls, filename, fraction, outdir='.', outfile=None):
        reader = cls.vti_file_to_reader(filename)
        resizer = cls.vti_downsample(reader, fraction)
        if not outfile:
            infile = Path(filename)
            inname = infile.name
            outfile = str(Path(outdir) / infile.with_name(
                'ds_{f:02d}_{name}'.format(f=int(fraction*100), name=inname)))
        cls.write_vti_from_reader(resizer, outfile)

    @classmethod
    def vti_file_to_pvti(cls, filename, outfile, number_of_pieces):
        reader = cls.vti_file_to_reader(filename)
        cls.write_pvti_from_reader(reader, outfile, number_of_pieces)

    def expand_archive(self, url, filename, scratch_subdir_name):
        # fetch and unzip the zip/7z file
        scratch_dir = self.base_scratch_directory / scratch_subdir_name
        expanded_dir = scratch_dir / 'expanded'
        expanded_dir.mkdir(parents=True, exist_ok=True)
        if url.startswith('/'):
            url = parse.urlunparse(['https', self.host, url, '', '', ''])
        src = request.urlopen(url)
        destpath = scratch_dir / filename
        dest = destpath.open(mode='wb')
        while True:
            buf = src.read(102400)
            if len(buf) < 1:
                break
            dest.write(buf)
        src.close()
        try:
            Archive(destpath).extractall(expanded_dir)
        except BadZipFile as ex:
            logging.warning('got zip error on file {f}: {ex}; trying alternative'
                            .format(f=str(filename), ex=str(ex)))
            self.jar_unzip(destpath, expanded_dir)
        except PatoolError as ex:
            logging.warning("couldn't expand {f} - assuming not compressed/zipped/etc".format(
                f = destpath))
            (expanded_dir / destpath.name).symlink_to(destpath)
                            
        return(expanded_dir)

    def jar_unzip(self, srcfile, destdir):
        # this is a horrible kludge to get around Archive's
        # false-positive zip bomb errors on large files
        subprocess.run(['jar', '-xf', srcfile], check=True, cwd=str(destdir))

    def archive_to_vti_reader(self, url, filename, scratch_subdir_name):
        expanded_dir = self.expand_archive(url, filename, scratch_subdir_name)
        if expanded_dir is not None:
            viz_reader = readers.new_image_reader(expanded_dir)
            if viz_reader is not None:
                return viz_reader.get_vti_reader()
        return None

    @classmethod
    def find_best_size(cls, reader, target_size):
        reader.Update()
        orig_size = reader.GetOutputDataObject(0).GetNumberOfPoints()
        if orig_size <= target_size:
            return(1.0)
        return round(pow(target_size / orig_size, .333), 2)

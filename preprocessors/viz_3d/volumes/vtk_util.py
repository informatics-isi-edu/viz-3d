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
    def __init__(self, host, source_file_url, source_file_name, rid, base_scratch_directory):
        self.host = host
        self.source_file_url = source_file_url
        self.source_file_name = source_file_name
        self.rid = rid
        self.scratch_directory = Path(base_scratch_directory) / self.host / self.rid
        self.reader = None

    # generates a filename of the form
    #   /scratch_dir/image_id/filename[_downsample].vti
    def image_file_name(self, downsample=None):
        filename = Path(self.source_file_name).stem
        if downsample:
            filename = filename + '_' + str(downsample)
        return((self.scratch_directory / filename)
               .with_suffix('.vti').as_posix())

    def clean_scratch_files(self):
        shutil.rmtree(
            self.scratch_directory.as_posix(), ignore_errors=True)

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
    def get_vti_writer(cls, reader, outfile):
        writer = vtk.vtkXMLImageDataWriter()
        writer.SetFileName(outfile)
        writer.SetInputConnection(reader.GetOutputPort())
        return writer

    @classmethod
    def vti_file_to_reader(cls, filename):
        reader = vtk.vtkXMLImageDataReader()
        reader.SetFileName(filename)
        return(reader)

    def vti_downsample(self, fraction):
        if fraction == 1.0:
            return(self.reader)
        if fraction <= 0 or fraction > 1:
            raise ValueError('fraction should be between 0 and 1')
        resizer = vtk.vtkImageResize()
        resizer.SetInputConnection(self.reader.GetOutputPort())
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

    def expand_archive(self, url, filename):
        # fetch and unzip the zip/7z file
        expanded_dir = self.scratch_directory / 'expanded'
        expanded_dir.mkdir(parents=True, exist_ok=True)
        if self.source_file_url.startswith('/'):
            self.source_file_url = parse.urlunparse(
                ['https', self.host, self.source_file_url, '', '', ''])

        src = request.urlopen(self.source_file_url)
        destpath = self.scratch_directory / filename
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

    def archive_to_vti_reader(self):
        expanded_dir = self.expand_archive(self.source_file_url, self.source_file_name)
        if expanded_dir is not None:
            viz_reader = readers.new_image_reader(expanded_dir)
            if viz_reader is not None:
                self.reader = viz_reader.get_vti_reader()
        return self.reader

    def find_best_size(self, target_voxels):
        self.reader.Update()
        self.original_voxels = self.reader.GetOutputDataObject(0).GetNumberOfPoints()
        if self.original_voxels <= target_voxels:
            return(1.0)
        return round(pow(target_voxels / self.original_voxels, .333), 2)

    def resize_and_write(self, fraction):
        resizer = self.vti_downsample(fraction)
        outfile = self.image_file_name(int(fraction * 100))
        writer = self.get_vti_writer(resizer, outfile)
        writer.Write()
        return {
            "filename": outfile,
            "downsample_percent": int(fraction * 100),
            "source_voxels": self.original_voxels,
            "processed_voxels": writer.GetInput().GetNumberOfPoints()
        }

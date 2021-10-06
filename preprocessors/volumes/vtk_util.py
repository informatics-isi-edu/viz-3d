import vtk
from urllib import request, parse
from pathlib import Path
from pyunpack import Archive
from zipfile import BadZipFile
import sys
import re
import os
from ctypes import *
import logging
import subprocess


class VtkUtil:

    # scratch_directory is a directory with lots of space for scratch files
    # host is just used to expand relative urls
    def __init__(self, host, scratch_directory):
        self.host = host
        self.base_scratch_directory = Path(scratch_directory)

    # read a directory of tiff files and write a vti file
    # without any additional processing - basically:
    #   dir_to_vtk_array | tiff_files_to_reader | write_vti_from_reader
    @classmethod
    def tiff_dir_to_vti_reader(cls, indir):
        inpath = Path(indir)
        if inpath.is_dir():
            files = cls.dir_to_vtk_array(inpath)
        else:
            raise ValueError('{dir} is not a directory'.format(dir=indir))
        return(cls.tiff_files_to_reader(files))

    # generates a filename of the form
    #   /scratch_dir/scratch_subdir/filename[_downsample].vti
    def make_vti_file_name(self, scratch_subdir, filename, downsample=None):
        filename = Path(filename).stem
        if downsample:
            filename = filename + '_' + str(downsample)
        return(str((self.base_scratch_directory / scratch_subdir / filename)
                   .with_suffix('.vti')))

    # list the tiff files in a directory
    @classmethod
    def dir_to_vtk_array(cls, dirpath, suffixes=['.tif', '.tiff']):
        a = vtk.vtkStringArray()
        for f in sorted(dirpath.glob('*')):
            if f.suffix.lower() in suffixes:
                a.InsertNextValue(str(f))
        return(a)

    # turn a list of tiff files into a vtkTIFFReader object
    # you should only use this if you want to use the reader in a pipeline;
    @classmethod
    def tiff_files_to_reader(cls, tiff_files):
        reader = vtk.vtkTIFFReader()
        buf = bytearray(15000000000)
        reader.SetMemoryBuffer(buf)
        reader.SetFileNames(tiff_files)
        reader.SetFileDimensionality(2)
        reader.SetFileNameSliceSpacing(1)
        reader.SetDataSpacing(1, 1, 1)
        return(reader)

    # convert a vtkTIFFReader object to a set of parallelized vti files
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

    # turn a vtkTIFFReader object into a vti file
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

    def archive_to_tiff_dir(self, url, filename, scratch_subdir_name):
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
        # locate the tiff directory
        return(self.find_tiff_dir(expanded_dir))

    def jar_unzip(self, srcfile, destdir):
        # this is a horrible kludge to get around Archive's
        # false-positive zip bomb errors on large files
        subprocess.run(['jar', '-xf', srcfile], check=True, cwd=str(destdir))

    def find_tiff_dir(self, dir):
        if len(list(dir.glob('*.tif'))) > 0 or len(list(dir.glob('*.tiff'))) > 0:
            return(dir)
        for child in dir.iterdir():
            result = self.find_tiff_dir(child)
            if result:
                return(result)
        return None

    def archive_to_vti_reader(self, url, filename, scratch_subdir_name):
        tiff_dir = self.archive_to_tiff_dir(url, filename, scratch_subdir_name)
        return (self.tiff_dir_to_vti_reader(tiff_dir) if tiff_dir else None)

    @classmethod
    def find_best_size(cls, reader, target_size):
        reader.Update()
        orig_size = reader.GetOutputDataObject(0).GetNumberOfPoints()
        if orig_size <= target_size:
            return(1.0)
        return round(pow(target_size / orig_size, .333), 2)
import vtk
import sys
import argparse

def main(filename):
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(filename)
    reader.Update()
    print(reader.GetOutputDataObject(0).GetNumberOfPoints())

if __name__ == '__main__':
    parser = argparse.ArgumentParser("Just report the number of voxels in an image", None, 1)
    parser.add_argument('filename')
    args = parser.parse_args()
    main(args.filename)

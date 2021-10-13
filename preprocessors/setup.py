from setuptools import setup

# aiohttp is only listed here because vtk (indirectly) requires it,
# and by default, it picks up an incompatible version.

setup(
    name='viz_3d',
    description='3d visualization tools',
    version="0.1",
    packages=['viz_3d', 'viz_3d.volumes'],
    install_requires=[
        'deriva',
        'vtk',
        'pyunpack',
        'aiohttp<4.0.0',
        'patool'
    ],
    scripts=['bin/process-3d-images', 'bin/count-voxels']
)

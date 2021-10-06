from vtk_util import VtkUtil
from deriva_3d_util import Deriva3DUtil
from deriva.core import BaseCLI
import argparse
import json
import traceback
import sys
import signal
import logging


def main(host, target_voxel_count, status, rids, config_file):
    du = Deriva3DUtil(host, config_file)
    vu = VtkUtil(host, du.get_scratch_directory())
    rids = set(rids)
    if len(rids) == 0:
        status = status if status else 'new'
    if status:
        rids = rids.union(set(du.get_rids_with_status(status)))
        for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGABRT,
                    signal.SIGSEGV, signal.SIGBUS, signal.SIGQUIT, signal.SIGIO]:
            signal.signal(sig, signal_handler)

    for rid in rids:
        try:
            print('Processing {rid}'.format(rid=rid))
            process_one_image(rid, du, vu, target_voxel_count)
        except Exception as ex:
            logging.error(str(ex))
            du.update_status(rid, 'error', ex)


def signal_handler(self, signal, frame=None):
    raise InterruptedError('got signal {sig}'.format(sig=signal.strsignal(signal)))


def process_one_image(rid, du, vu, target_voxel_count):
    logging.info('processing RID {r}'.format(r=rid))
    du.update_status(rid, 'in progress')
    file_info = du.rid_to_file_info(rid)
    reader = vu.archive_to_vti_reader(file_info['source_file_url'],
                                      file_info['source_file_name'], rid)
    fraction = vu.find_best_size(reader, target_voxel_count)
    resizer = vu.vti_downsample(reader, fraction)
    outfile = vu.make_vti_file_name(rid, file_info['source_file_name'],
                                    int(fraction * 100))
    vu.write_vti_from_reader(resizer, outfile)
    du.upload_processed_file(rid, outfile, int(fraction * 100))
    du.update_status(rid, 'success')


if __name__ == '__main__':

    cli = BaseCLI("""Process one or more volumetric 3D images for use with VTK.
    Query information about source images, create converted/downsampled files,
    upload them to and register them in deriva.""", None, 1, hostname_required=True)
    cli.parser.add_argument('--target-voxel-count', type=int, default=60000000,
                            help='target size (in voxels) for downsampled file')
    cli.parser.add_argument('--status', default=None,
                            help='process records with this processing status')
    cli.parser.add_argument('rid', nargs='*', default=None,
                            help='process records with this/these RID(s)')
    args = cli.parse_cli()
    main(args.host, args.target_voxel_count, args.status, args.rid, args.config_file)

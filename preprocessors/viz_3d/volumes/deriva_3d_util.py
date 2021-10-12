from deriva.core import DerivaServer, get_credential, HatracStore
from deriva.core.utils import hash_utils
from deriva.core.datapath import DataPathException
from urllib import request, parse
from pyunpack import Archive
from pathlib import Path
import json


class Deriva3DUtil:
    def __init__(self, host, config_filename=None):
        self.host = host
        self.config_path = Path(config_filename) if config_filename \
            else Path.home() / 'viz_3d_config.json'
        all_config = json.load(self.config_path.open())
        self.config = all_config.get(host)
        if self.config is None:
            raise ValueError('no configuration found for host {h}'.format(h=host))
        credential = get_credential(host)
        self.hatrac_server = HatracStore('https', host, credential)
        server = DerivaServer('https', host, credential)
        catalog_id = self.config.get('catalog_id')
        if catalog_id is None:
            raise ValueError('no catalog_id specified for host {h} in file {f}'
                             .format(h=host), f=str(self.config_path))
        self.catalog = server.connect_ermrest(catalog_id)
        self.pb = self.catalog.getPathBuilder()
        scratch_directory = self.config.get('scratch_directory')
        if scratch_directory is None:
            raise ValueError('no scratch_directory specified for host {h} in file {f}'
                             .format(h=host), f=str(self.config_path))
        self.base_scratch_directory = Path(scratch_directory) / host

        su = self.config.get('status_update')
        self.status_table = None
        if su:
            self.status_table = self.pb.schemas.get(
                su.get('schema')).tables.get(su.get('table'))
            self.status_column_name = su['column']
            self.status_column_detail_name = su.get('detail_column')

        self.backpointer_table = None
        bp = self.config.get('backpointer')
        if bp and bp.get('schema'):
            self.backpointer_table = self.pb.schemas.get(
                bp.get('schema')).tables.get(bp.get('table'))
            self.backpointer_column_name = bp['column']

    def get_scratch_directory(self):
        return(str(self.base_scratch_directory))

    def rid_to_file_info(self, rid):
        self.validate_rid(rid)
        query = self.config.get('rid_to_file_query')
        if query is None:
            raise ValueError(
                'no rid_to_file_query specified for host {h} in file {f}'
                .format(h=self.host), f=str(self.self.config_path))
        entries = self.catalog.get(query.format(rid=rid)).json()
        if len(entries) != 1:
            raise ValueError("query for RID {r} didn't return a unique entry"
                             .format(r=rid))
        result = entries[0]
        if not (result.get('source_file_url') and result.get('source_file_name')):
            raise ValueError(
                'source_file_name or source_file_url is missing from query results for RID {r}'
                .format(r=rid))
        return(result)

    def upload_processed_file(self, rid, sourcefile, downsample_percent):
        self.validate_rid(rid)
        sourcepath = Path(sourcefile)
        destpath = self.config['base_hatrac_path'] + '/' + rid + '/' + sourcepath.name
        url = self.hatrac_server.put_obj(destpath, sourcepath, parents=True,
                                         content_type='application/x-vti')
        table = self.pb.schemas.get(self.config['processed_file_schema'])\
            .tables.get(self.config['processed_file_table'])
        md5 = hash_utils.compute_file_hashes(sourcepath, hashes=['md5'])['md5'][0]
        row = {
            self.config['source_rid_column']: rid,
            self.config['url_column']: url,
        }
        if self.config.get('filename_column'):
            row[self.config['filename_column']] = sourcepath.name
        if self.config.get('md5_column'):
            row[self.config['md5_column']] = md5
        if self.config.get('size_column'):
            row[self.config['size_column']] = sourcepath.stat().st_size
        if self.config.get('downsample_percent_column'):
            row[self.config['downsample_percent_column']] = downsample_percent

        if (self.config['source_columns_to_copy'] and
            len(self.config['source_columns_to_copy']) > 0):
            response = self.hatrac_server.get(
                self.config['resolver_prefix'] + rid)
            source_data = response.json()
            if len(source_data) != 1:
                raise ValueError("can't get unique result from {u}"
                                 .format(u=resolver_url))
            sourcerow = source_data[0]

            for col in self.config['source_columns_to_copy']:
                row[col] = sourcerow[col]
        new_row = None
        try:
            new_row = table.insert(
                [row],
                defaults=set(self.config.get('columns_to_leave_at_defaults')),
                nondefaults=set(self.config.get('nondefaults'))
            )[0]
        except DataPathException as ex:
            # if the problem is that this is a duplicate, ignore it.
            md5_col = self.pb.schemas.get(self.config['processed_file_schema'])\
                .tables.get(self.config['processed_file_table'])\
                .column_definitions.get(self.config['md5_column'])
            entities = table.filter(md5_col == row[self.config['md5_column']])\
                            .entities()
            if len(entities) != 1:
                raise ex
            if entities[0].get(self.config['source_rid_column']) != \
               row[self.config['source_rid_column']]:
                raise ex

        if new_row and self.backpointer_table:
            self.backpointer_table.update([
                {
                    'RID': rid,
                    self.backpointer_column_name: new_row['RID']
                }
            ])

    @classmethod
    def get_column(cls, table, colname):
        return(table.column_definitions.get(colname))

    @classmethod
    def validate_rid(cls, rid):
        for char in rid:
            if not(char.isalnum() or char == '-'):
                raise ValueError('Bad RID ' + rid)

    def get_rids_with_status(self, status):
        if self.status_table is None:
            raise ValueError('No status table configured')
        status_column = \
            self.status_table.column_definitions[self.status_column_name]
        entities = self.status_table.filter(status_column == status).entities()
        rids = []
        for row in entities:
            rids.append(row['RID'])
        return(rids)

    def update_status(self, rid, status, exception=None):
        if self.status_table:
            row = {
                'RID': rid,
                self.status_column_name: status
            }
            if self.status_column_detail_name:
                row[self.status_column_detail_name] = str(exception) \
                    if exception else None
            self.status_table.update([row])

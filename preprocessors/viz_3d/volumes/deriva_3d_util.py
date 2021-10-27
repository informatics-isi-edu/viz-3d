from deriva.core import DerivaServer, get_credential, HatracStore
from deriva.core.utils import hash_utils
from deriva.core.datapath import DataPathException
from urllib import request, parse
from pathlib import Path
import json
import sys

class Deriva3DUtil:
    TAG = 'tag:isrd.isi.edu,2021:viz-3d-display'
    DEFAULT_RESOLVER_PREFIX = '/id/'
    def __init__(self, host, schema_name, table_name, catalog_id=1, public_records_only=True):
        print("host '{h}', schema '{s}', table '{t}', catalog '{c}'".format(
            h=str(host), s=str(schema_name), t=str(table_name), c=str(catalog_id)))
        self.host = host
        credential = get_credential(host)
        self.hatrac_server = HatracStore('https', host, credential)
        server = DerivaServer('https', host, credential)
        self.catalog = server.connect_ermrest(catalog_id)
        self.pb = self.catalog.getPathBuilder()
        self.config = self.get_config(schema_name, table_name)

        if public_records_only:
            read_server = DerivaServer('https', host, None)
            self.read_catalog = read_server.connect_ermrest(catalog_id)
            self.read_pb = self.read_catalog.getPathBuilder()
        else:
            self.read_catalog = self.catalog
            self.read_pb = self.pb

        su = self.config.get('status_update')
        self.status_table = None
        if su:
            self.status_table = self.pb.schemas.get(
                su.get('schema')).tables.get(su.get('table'))
            self.read_status_table = self.read_pb.schemas.get(
                su.get('schema')).tables.get(su.get('table'))
            self.status_column_name = su['column']
            self.status_column_detail_name = su.get('detail_column')

            self.status_values = dict()
            if su.get('status_value_schema') and su.get('status_value_table'):
                status_rows = \
                    self.read_pb\
                        .schemas.get(su.get('status_value_schema'))\
                        .tables.get(su.get('status_value_table'))\
                        .entities()
                for row in status_rows:
                    self.status_values[row['Name']] = row['ID']
                json.dump(self.status_values, sys.stdout, indent=4)
                

        self.backpointer_table = None
        bp = self.config.get('backpointer')
        if bp and bp.get('schema'):
            self.backpointer_table = self.pb.schemas.get(
                bp.get('schema')).tables.get(bp.get('table'))
            self.backpointer_column_name = bp['column']

    def status(self, status_name):
        val = self.status_values.get(status_name)
        return val if val is not None else status_name

    def get_config(self, schema_name, table_name):
        model = self.catalog.getCatalogModel()
        config_table = model.table(schema_name, table_name)

        config = config_table.annotations.get(self.TAG)        
        if config is None:
            raise Deriva3DUtilConfigError(
                'No {tag} annotation found for table {s}:{t}'.format(
                    tag=self.TAG, s=schema_name, t=table_name))
        if config.get('resolver_prefix') is None:
            config['resolver_prefix'] = DEFAULT_RESOLVER_PREFIX
        for key in [
                'rid_to_file_query',
                'processed_file']:
            if config.get(key) is None:
                raise Deriva3DUtilConfigError(
                    '{attr} missing from {tag} annotation for table {s}:{t}'.format(
                        attr=key, tag=self.TAG, s=schema_name, t=table_name))
        pfconfig = config.get('processed_file')
        for key in [
                'schema',
                'table',
                'source_rid_column',
                'hatrac_parent',
                'url_column']:
            if pfconfig.get(key) is None:
                raise Deriva3DUtilConfigError(
                    '{attr} missing from processed_file attributes in  {tag} annotation for table {s}:{t}'\
                    .format(attr=key, tag=self.TAG, s=schema_name, t=table_name))
        return(config)
        
    def rid_to_file_info(self, rid):
        self.validate_rid(rid)
        query = self.config.get('rid_to_file_query')
        if query is None:
            raise ValueError(
                'no rid_to_file_query specified for host {h} in file {f}'
                .format(h=self.host), f=str(self.self.config_path))
        entries = self.read_catalog.get(query.format(rid=rid)).json()
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
        processed_file_config = self.config.get('processed_file')
        destpath = processed_file_config['hatrac_parent'] + '/' + rid + '/' + sourcepath.name
        url = self.hatrac_server.put_obj(destpath, sourcepath, parents=True,
                                         content_type='application/x-vti')
        table = self.pb.schemas.get(processed_file_config['schema'])\
            .tables.get(processed_file_config['table'])
        md5 = hash_utils.compute_file_hashes(sourcepath, hashes=['md5'])['md5'][0]
        row = {
            processed_file_config['source_rid_column']: rid,
            processed_file_config['url_column']: url,
        }
        if processed_file_config.get('filename_column'):
            row[processed_file_config['filename_column']] = sourcepath.name
        if processed_file_config.get('md5_column'):
            row[processed_file_config['md5_column']] = md5
        if processed_file_config.get('size_column'):
            row[processed_file_config['size_column']] = sourcepath.stat().st_size
        if processed_file_config.get('downsample_percent_column'):
            row[processed_file_config['downsample_percent_column']] = downsample_percent

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
        processed_row = None
        try:
            processed_row = table.insert(
                [row],
                defaults=set(self.config.get('columns_to_leave_at_defaults')),
                nondefaults=set(self.config.get('nondefaults'))
            )[0]
        except DataPathException as ex:
            # if the problem is that this is a duplicate, ignore it.
            md5_col = self.pb.schemas.get(processed_file_config['schema'])\
                .tables.get(processed_file_config['table'])\
                .column_definitions.get(processed_file_config['md5_column'])
            entities = table.filter(md5_col == row[processed_file_config['md5_column']])\
                            .entities()
            if len(entities) != 1:
                raise ex
            processed_row = entities[0]
            if processed_row.get(processed_file_config['source_rid_column']) != \
               row[processed_file_config['source_rid_column']]:
                raise ex

        if self.backpointer_table:
            self.backpointer_table.update([
                {
                    'RID': rid,
                    self.backpointer_column_name: processed_row['RID']
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
        if self.read_status_table is None:
            raise ValueError('No status table configured')
        status_column = \
            self.read_status_table.column_definitions[self.status_column_name]
        entities = self.read_status_table.filter(status_column == self.status(status))\
                                         .entities()
        rids = []
        for row in entities:
            rids.append(row['RID'])
        return(rids)

    def update_status(self, rid, status, exception=None):
        if self.status_table:
            row = {
                'RID': rid,
                self.status_column_name: self.status(status)
            }
            if self.status_column_detail_name:
                row[self.status_column_detail_name] = str(exception) \
                    if exception else None
            self.status_table.update([row])

class Deriva3DUtilConfigError(Exception):
    pass

import pandas as pd
import os

class CDASHTool:
    def __init__(self, standards_dir: str):
        self.standards_dir = standards_dir
        self.fields_df = pd.read_csv(os.path.join(self.standards_dir, "cdash_fields.csv"))
        self.codelists_df = pd.read_csv(os.path.join(self.standards_dir, "cdash_codelists.csv"))

    def get_domain_fields(self, domain: str):
        return self.fields_df[self.fields_df['domain'] == domain].to_dict('records')

    def get_codelists(self, field_ids: list):
        return self.codelists_df[self.codelists_df['field_name'].isin(field_ids)].to_dict('records')

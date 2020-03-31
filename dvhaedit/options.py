from dvhaedit.dicom_editor import get_uid_prefixes


class Options:
    def __init__(self):
        # DICOM options
        self.prefix = ''
        self.prefix_dict = get_uid_prefixes()
        self.entropy_source = ''

        # Random Number generator
        self.rand_digits = 5

import configparser
import re
import sys
import os
import json
import sys
import pathlib
from matplotlib import pylab as plt
import numpy as np
import pandas as pd
import seaborn as sns
import random
import nbformat
from nbconvert import MarkdownExporter
import logs
from copy import deepcopy


config = configparser.ConfigParser()
logging = logs.setup()


def load_notebooks(directory: str) -> dict[str, dict]:
    data: dict[str, dict] = {}

    for file in pathlib.Path(directory).rglob('*.ipynb'):
        """Notebook must be named '<exercise>_<hex_id>.ipynb' with <hex_id> matching the notebook id form the csv file."""
        notebook_hex = re.match(r'.*_([a-fA-F0-9]+)\.ipynb', file.name)
        if not notebook_hex:
            logging.warning(f"Notebook {file} does not match the naming convention and will be skipped.")
            continue
        notebook_hex = notebook_hex.group(1)
        with open(file) as f:
            logging.debug(f"Loading notebook '{file.stem}' with id='{notebook_hex}'")
            # Reading Notebook as nbformat which is basically like json.read(f) but intended way; main difference
            # ist that cell contents are not being read as an array of lines but as a string with newlines
            data[notebook_hex] = nbformat.read(f, as_version=4)

    logging.info(f"Loaded {len(data)} notebooks.")
    return data

def compare_expert_ranking(path: str) -> pd.DataFrame:
    points: pd.DataFrame = pd.read_csv(path)

    df = points.loc[:, ['id', 'total_points']]

    df['inital_order'] = df['id'].map(lambda x: check_idxs.index(x))
    df['llm-heapsort_rank'] = df['id'].map(lambda x: cw_data_sorted[::1].index(x))
    df.set_index('id', inplace=True)




if __name__ == "__main__":
    if len(sys.argv) <= 1:
        logging.error("Usage: python execute.py <experiment_config>")
        exit(1)

    for i in range(1, len(sys.argv)):
        config_file = sys.argv[1]
        if os.path.isfile(config_file):
            try:
                config.read(config_file)
                load_notebooks(config['Data']['data_path'] + config['Data']['exercises'])

            except Exception as e:
                logging.error(f"Error reading config file: {e}")
                exit(1)
        else:
            logging.error(f"Config file '{config_file}' not found.")
            exit(1)
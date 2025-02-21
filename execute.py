import configparser
import logging
import os
import pathlib
import random
import re
import sys

import nbformat
import pandas as pd
from nbformat import NotebookNode

from logs import add_file_handler
from logs import global_logger as logging
from llm import PRPmodel
from sort import heapsort
from filter import filter_images, filter_output_cells, format_markdown

config = configparser.ConfigParser()

def load_notebooks(directory: str) -> dict[str, NotebookNode]:
    data: dict[str, NotebookNode] = {}

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


def compare_expert_ranking(path: str, check_idxs: list, data_sorted: list) -> pd.DataFrame:
    points: pd.DataFrame = pd.read_csv(path)

    df = points.loc[:, ['id', 'total_points']]

    df['randomized'] = df['id'].map(lambda x: check_idxs.index(x))
    df['llm'] = df['id'].map(lambda x: data_sorted[::1].index(x))
    df.set_index('id', inplace=True)

    return df

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        logging.error("Usage: python execute.py <experiment_config>")
        exit(1)

    for i in range(1, len(sys.argv)):
        config_file = sys.argv[i]
        if os.path.isfile(config_file):
            try:
                config.read(config_file)
                logging.info(f"Starting experiment from config file '{config_file}'")
            except Exception as e:
                logging.error(f"Error reading config file: {e}")
                continue
        else:
            logging.error(f"Config file '{config_file}' not found.")
            continue

        # create sepearate log file for each experiment
        experiment_name = config_file.split("/")[-1][:-4]
        add_file_handler(logging, f'{experiment_name}.log')
        logging.info(f"Running experiment {experiment_name}.")

        exercise_dir = config['Data']['data_path'] + config['Data']['exercises']
        notebooks: dict[str, NotebookNode] = load_notebooks(exercise_dir)

        ### Filter
        if config.getboolean('Data Preprocessing', 'filter_output_images'):
            notebooks = filter_images(notebooks)
            logging.info('Images filtered.')
        if config.getboolean('Data Preprocessing', 'filter_output_cells'):
            notebooks = filter_output_cells(notebooks)
            logging.info('Output cells filtered.')
        match config.get('Data Preprocessing', 'notebook_format', fallback='ipynb-json'):
            case 'ipynb-json':
                pass
            case 'markdown':
                notebooks = format_markdown(notebooks)
                logging.info('Markdown formatted.')

        prp = PRPmodel(config, notebooks)

        random_seed: int | None = config.getint('Data', 'random_seed', fallback=2797)
        random.seed(random_seed)
        logging.info(f'Random seed set to {random_seed}.')

        if config.getboolean('Data', 'shuffle_notebooks'):
            check_idxs = list(notebooks.keys())
            random.shuffle(check_idxs)
            logging.info('Notebooks shuffled.')
        else:
            check_idxs = list(notebooks.keys())

        logging.info(f'Initial order of notebooks: {check_idxs}')

        logging.info(f'Starting comparison of notebooks...')
        if config.getboolean('Prompting', 'majority_vote'):
            data_sorted = heapsort(check_idxs, prp.sort_function_majority_vote)
        else:
            data_sorted = heapsort(check_idxs, prp.sort_function)

        logging.info(f'Sorting finished. Final order of notebooks: {data_sorted}')

        expert_ranking_csv = config['Data']['data_path'] + config['Data']['expert_ranking']
        df = compare_expert_ranking(expert_ranking_csv, check_idxs, data_sorted)

        logging.info(f'Expert ranking compared to LLM ranking:')
        logging.info(f'df:\n{df}')
        logging.info(df.corr(method='kendall'))

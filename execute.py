import configparser
import logging
import os
import pathlib
import random
import re
import sys
from itertools import permutations, combinations

import nbformat
import numpy as np
import pandas as pd
from nbformat import NotebookNode

from compare import position_pairs
from logs import add_file_handler
from logs import global_logger as logging
from llm import PRPmodel
from sort import heapsort, quicksort, bubble_sort
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

    if config.getboolean('Data', 'shuffle_notebooks'):
        df['randomized'] = df['id'].map(lambda x: check_idxs.index(x))
    else:
        df['initial_order'] = df['id'].map(lambda x: check_idxs.index(x))

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

        # create separate log file for each experiment
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

        if config.get('Data Preprocessing', 'exclude_notebooks', fallback=None):
            exclude_notebooks = [s.strip().removeprefix("'").removesuffix("'") for s in
                          config['Data Preprocessing']['exclude_notebooks'].split(',')]
            logging.info(f'Excluding notebooks: {exclude_notebooks}')
            notebooks = {k: v for k, v in notebooks.items() if k not in exclude_notebooks}

        prp = PRPmodel(config, notebooks)

        random_seed: int | None = config.getint('Data', 'random_seed', fallback=2797)
        random.seed(random_seed)
        logging.info(f'Random seed set to {random_seed}.')

        if config.getboolean('Data', 'shuffle_notebooks'):
            check_idxs = list(notebooks.keys())
            random.shuffle(check_idxs)
            logging.info('Notebooks shuffled.')
        elif config.get('Data', 'initial_order', fallback=None):
            check_idxs = [s.strip().removeprefix("'").removesuffix("'") for s in config['Data']['initial_order'].split(',')]
        else:
            check_idxs = list(notebooks.keys())

        logging.info(f'Initial order of notebooks: {check_idxs}')

        ### Sorting and Comparison
        logging.info(f'Starting comparison of notebooks...')

        compare_function: callable = None
        if config.getboolean('Prompting', 'majority_vote'):
            compare_function = prp.llm_majority_vote
        else:
            compare_function = prp.llm_compare

        if config.get('Sorting', 'algorithm', fallback=None):
            algorithm_name: str = config.get('Sorting', 'algorithm')
            algorithm: callable = None
            if algorithm_name == 'heapsort':
                algorithm = heapsort
            elif algorithm_name == 'quicksort':
                algorithm = quicksort
            elif algorithm_name == 'bubble_sort':
                algorithm = bubble_sort
            else:
                logging.error(f'Unknown sorting algorithm: {algorithm_name}')
                exit(1)

            logging.info(f'Sorting notebooks with {algorithm_name} using {compare_function.__name__}.')
            data_sorted = algorithm(check_idxs, compare_function)
            logging.info(f'Sorting finished. Final order of notebooks: {data_sorted}')

            expert_ranking_csv = config['Data']['data_path'] + config['Data']['expert_ranking']
            df = compare_expert_ranking(expert_ranking_csv, check_idxs, data_sorted)

            # Compare expert ranking to LLM ranking
            logging.info(f'Expert ranking compared to LLM ranking:')
            logging.info(f'df:\n{df}')
            logging.info(df.corr(method='kendall'))

        elif config.get('Comparing', 'algorithm', fallback=None):
            algorithm_name: str = config.get('Comparing', 'algorithm')
            algorithm: callable = None
            if algorithm_name == 'position_pairs':
                algorithm = position_pairs
            else:
                logging.error(f'Unknown sorting algorithm: {algorithm_name}')
                exit(1)

            logging.info(f'Comparing notebook pairs with {algorithm_name} using {compare_function.__name__}.')

            all_nb_pairs: list[tuple] = list(combinations(check_idxs, 2))
            n_pairs: int = config.getint('Comparing', 'pairs', fallback=len(all_nb_pairs))
            if config.getboolean('Data', 'shuffle_notebooks'):
                random.shuffle(all_nb_pairs)

            selected_nb_pairs: list[tuple] = all_nb_pairs[:n_pairs]
            logging.info(f'Selected {n_pairs} of ouf {len(all_nb_pairs)} notebook pairs for comparison: {selected_nb_pairs}')

            consistency_list = algorithm(selected_nb_pairs, compare_function)
            # combine results with selected_nb_pairs
            results = list(zip(selected_nb_pairs, consistency_list))
            logging.info(f'Comparison results: {results}')
            logging.info(f'Consistency list: {consistency_list}')
            logging.info(f'Out of {len(consistency_list)} comparisons made, {sum(consistency_list)} were consistent, meaning the LLM choose one over the other independent of its appearance in the prompt.')

        else:
            logging.error('No sorting or comparing algorithm specified.')
            exit(1)

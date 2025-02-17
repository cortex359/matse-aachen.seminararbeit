from copy import deepcopy
import nbformat
from nbconvert import MarkdownExporter

def filter_images(data_array):
    """Sets the image data to None in the output of code cells."""
    data = deepcopy(data_array)
    for k, v in data.items():
        for cell in v['cells']:
            if cell['cell_type'] == 'code' and 'outputs' in cell:
                for output in cell['outputs']:
                    if 'data' in output and 'image/png' in output['data']:
                        # remove image from data
                        output['data']['image/png'] = None
    return data

def filter_output_cells(data_array):
    """Removes the output of code cells."""
    data = deepcopy(data_array)
    for k, v in data.items():
        for i, cell in enumerate(v['cells']):
            if cell['cell_type'] == 'code' and 'outputs' in cell:
                #print(cell['outputs'])
                data[k]['cells'][i]['outputs'] = []
    return data



def format_markdown(data_array):
    """Formats the markdown cells."""
    data = {}

    for k, v in data_array.items():
        markdown, _ = MarkdownExporter().from_notebook_node(v)
        data[k] = markdown

    return data
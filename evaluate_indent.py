import copy
import json
import os

import click

from pdf_struct import transition_labels
from pdf_struct.clustering import cluster_positions
from pdf_struct.pdf import load_pdfs
from pdf_struct.structure_evaluation import evaluate_structure, evaluate_labels
from pdf_struct.text import load_texts
from pdf_struct.transition_predictor import ListAction
from pdf_struct.utils import pairwise


@click.command()
@click.argument('file-type', type=click.Choice(('txt', 'pdf')))
def main(file_type: str):
    anno_dir = os.path.join('data', f'anno_{file_type}')
    print(f'Loading annotations from {anno_dir}')
    annos = transition_labels.load_annos(anno_dir)

    print('Loading and extracting features from raw files')
    if file_type == 'pdf':
        documents = load_pdfs(os.path.join('data', 'raw'), annos, dummy_feats=True)
        documents_pred = []
        for document in documents:
            horizontal_thresh = 10  # 10 points = 1em
            line_spacing_thresh = 2  # 2 points = 1ex / 2

            clusters_l, mappings_l = cluster_positions(
                [b.bbox[0] for b in document.text_boxes], horizontal_thresh)
            clusters_s, mappings_s = cluster_positions(
                [b1.bbox[1] - b2.bbox[1]
                 for b1, b2 in pairwise(sorted(document.text_boxes, key=lambda b: (
                    b.page, -b.bbox[1], b.bbox[0])))
                 if b1.page == b2.page],
                line_spacing_thresh
            )
            line_spacing = max(clusters_s, key=lambda c: len(c))

            labels = []
            pointers = []
            clusters = [clusters_l[mappings_l[document.text_boxes[0].bbox[0]]]]
            for i in range(1, len(document.text_boxes)):
                c_i = clusters_l[mappings_l[document.text_boxes[i].bbox[0]]]
                if clusters[-1] == c_i:
                    ls = document.text_boxes[i-1].bbox[1] - document.text_boxes[i].bbox[1]
                    if document.text_boxes[i-1].page == document.text_boxes[i].page and ls in line_spacing:
                        # normal line spacing
                        labels.append(ListAction.CONTINUOUS)
                    else:
                        labels.append(ListAction.SAME_LEVEL)
                    pointers.append(None)
                elif clusters[-1].mean < c_i.mean:
                    labels.append(ListAction.DOWN)
                    pointers.append(None)
                elif clusters[-1].mean > c_i.mean:
                    labels.append(ListAction.UP)
                    for j in range(i - 1, -1, -1):
                        if clusters[j] is not None and clusters[j] == c_i:
                            pointers.append(j)
                            break
                        # Disable non-matching cluster to avoid matching to counsins
                        clusters[j] = None
                    else:
                        pointers.append(-1)
                clusters.append(c_i)
            labels.append(ListAction.UP)
            pointers.append(-1)
            d = copy.deepcopy(document)
            d.labels = labels
            d.pointers = pointers
            documents_pred.append(d)

    else:
        raise NotImplementedError()
        documents = load_texts(os.path.join('data', 'raw'), annos)
        # implement it using "indent" value

    print(json.dumps(evaluate_structure(documents, documents_pred), indent=2))
    print(json.dumps(evaluate_labels(documents, documents_pred), indent=2))


if __name__ == '__main__':
    main()

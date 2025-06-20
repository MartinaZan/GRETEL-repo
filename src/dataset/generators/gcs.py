from os.path import join

import json
import numpy as np
import random

from src.dataset.generators.base import Generator
from src.dataset.instances.graph import GraphInstance

class GCS(Generator):
    def init(self):
        base_path = self.local_config['parameters']['data_dir']
        file_names = self.local_config['parameters']['data_file_name'] ## Added

        self._data_file_path = [join(base_path, file_name) for file_name in file_names] # join(base_path, self.local_config['parameters']['data_file_name'])
        self._data_label_name = self.local_config['parameters']['data_label_name']

        self.num_node_features = None

        self.dataset.node_features_map = None
        self.dataset.edge_features_map = None # rdk_edge_features_map()
        self.generate_dataset()

    def check_configuration(self):
        super().check_configuration()
        local_config=self.local_config

        if 'data_file_name' not in local_config['parameters']:
            raise Exception("The name of the data file must be given.")
       
        if 'data_label_name' not in local_config['parameters']:
            raise Exception("The name of the label column must be given.")

    # Funzione per la generazione del dataset, che chiama la funzione per la lettura dei dati dal json
    # def generate_dataset(self):
    #     if not len(self.dataset.instances):
    #         self._read(self._data_file_path)

    # Funzione per la generazione del dataset, che chiama la funzione per la lettura dei dati dal json
    def generate_dataset(self):
        if not len(self.dataset.instances):
            for item in self._data_file_path:
                self._read(item)

    def _read(self, path):
        if not len(self.dataset.instances):
            idx = 0
        else:
            idx = len(self.dataset.instances)

        # Apertura del file json con dati dei grafi.
        # Il dizionario comprende le seguenti chiavi:
        #    data.keys() --> dict_keys(['edge_mapping', 'node_ids', 'time_periods', 'target', 'series'])
        # 'target' contiene le true label per la classificazione
        # 'series' contiene i valori della serie temporale multivariata, da usare per definire le feature dei nodi
        data = json.load(open(path))

        self.num_node_features = len(data["series"][0])

        # Definizione di node e edge features map. Sono dei dizionari che contengono tante caratteristiche quante sono le feature.
        # self.dataset.node_features_map = {'attribute_0': 0}
        self.dataset.node_features_map = {f'attribute_{i}': i for i in range(self.num_node_features)}
        # self.dataset.edge_features_map =  # change me

        # Creazione di un grafo per ogni step temporale
        for t in data['time_periods']:
            # Creazione di adjacency e node feature matrix.
            # Alla funzione corr2graph vengono passati:
            #   - l'id del grafo (ossia l'indice temporale): t
            #   - le informazioni sugli archi al tempo t: data['edge_mapping']['edge_index'][str(t)]
            #   - le informazioni sui pesi al tempo t: data['edge_mapping']['edge_weight'][str(t)]
            #   - i valori della serie temporale al tempo t: data["series"][t]
            #   - self.dataset (per accedere a self.dataset.node_features_map e self.dataset.edge_features_map)
            A,X,W = corr2graph(t, data['edge_mapping']['edge_index'][str(t)], data['edge_mapping']['edge_weight'][str(t)], data["series"][t], data["target"][t], self.dataset)
            
            # Lettura della true label al tempo t (crisi/no crisi)
            y = data["target"][t]
            
            patient_id = data["patient"]
            record_id = data["record"]

            g = GraphInstance(
                id = idx,               # id grafo
                label = y,              # label crisi/no crisi
                data = A,               # data: n x n matrix where n is the number of nodes (i.e., it is the binary adjacency matrix)
                node_features = X,      # node_features: n x d matrix where d is the number of node features (per ora considero d = 1)
                edge_weights = W,       # edge_weights: n x n matrix containing the weight of each edge (i.e., it is the weighted adjacency matrix)
                graph_features = {},    # feature del grafo (per il momento, nessuna)
                time = t,               # id temporale
                patient_id = patient_id,
                record_id = record_id,
            )
            self.dataset.instances.append(g)

            idx = idx + 1
    
def corr2graph(id, data, weight, series, target, dataset):
    n_map = dataset.node_features_map
    # e_map = dataset.edge_features_map
    
    # Numero di nodi
    n = len(series[0])

    A = np.zeros((n, n))
    W = np.zeros((n, n))

    ##########################################################################

    if len(n_map) == 1:
        X = np.array(series).reshape(n, 1)
    else:
        X = np.fliplr(np.array(series).T)

    ##########################################################################

    # Scorre tutti gli archi e imposta matrice di adiacenza pesata (W) e binaria (A)
    for p, edge in enumerate(data):
        if np.abs(weight[p]) > 0 : # 0.3: # (condizione per threshold)
            W[edge[0], edge[1]] = np.abs(weight[p])
            A[edge[0], edge[1]] = 1 if weight[p] != 0 else 0

    # W deve essere un vettore, quindi lo flatteniamo
    W = W[W != 0].flatten()

    return A,X,W

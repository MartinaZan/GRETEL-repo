import copy
import sys

from src.core.explainer_base import Explainer
import numpy as np

from src.core.factory_base import get_instance_kvargs
from src.utils.cfg_utils import  init_dflts_to_of 

class DCESExplainer(Explainer):
    """The Distribution Compliant Explanation Search Explainer performs a search of 
    the minimum counterfactual instance in the original dataset instead of generating
    a new instance"""

    def check_configuration(self):
        super().check_configuration()

        dst_metric='src.evaluation.evaluation_metric_ged.GraphEditDistanceMetric'  ### PRIMA
        # dst_metric='src.evaluation.embedding_metrics.EmbeddingMetric'            ### DOPO

        # Check if the distance metric exist or build with its defaults:
        init_dflts_to_of(self.local_config, 'distance_metric', dst_metric)


    def init(self):
        super().init()

        self.distance_metric = get_instance_kvargs(self.local_config['parameters']['distance_metric']['class'], 
                                                    self.local_config['parameters']['distance_metric']['parameters'])
        
        # Parametro opzionale di lookback per explainer
        # self.lookback = self.local_config['parameters'].get('lookback', None)

    def explain(self, instance):
        input_label = self.oracle.predict(instance)

        # if the method does not find a counterfactual example returns the original graph
        min_ctf = instance

        # Iterating over all the instances of the dataset
        min_ctf_dist = sys.float_info.max
        for ctf_candidate in self.dataset.instances:
            # Considera solo stesso paziente, stesso record e tempo precedente (in caso cambia <= con <)
            if ctf_candidate.patient_id == instance.patient_id and ctf_candidate.record_id == instance.record_id and ctf_candidate.time <= instance.time:

                # candidate_label, graph_embeddings = self.oracle.predict(ctf_candidate, return_embeddings=True) ## Chiama oracle_base.predict

                candidate_label = self.oracle.predict(ctf_candidate) ## Chiama oracle_base.predict

                if input_label != candidate_label:
                    ctf_distance = self.distance_metric.evaluate(instance, ctf_candidate, self.oracle)
                    
                    if ctf_distance < min_ctf_dist:
                        min_ctf_dist = ctf_distance
                        min_ctf = ctf_candidate

        result = copy.deepcopy(min_ctf)
        result.id = instance.id

        return result
    

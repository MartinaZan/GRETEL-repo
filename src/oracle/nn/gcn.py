import torch.nn as nn
from torch_geometric.nn.aggr import MeanAggregation

from src.utils.torch.gcn import GCN


class DownstreamGCN(GCN):
   
    def __init__(self, node_features,
                 n_classes=2,
                 num_conv_layers=2,
                 num_dense_layers=2,
                 conv_booster=2,
                 linear_decay=2,
                 pooling=MeanAggregation()):
        
        super().__init__(node_features, num_conv_layers, conv_booster, pooling)
        
        self.num_dense_layers = num_dense_layers
        self.linear_decay = linear_decay
        self.n_classes = n_classes
        
        self.downstream_layers = self.__init__downstream_layers()
        
        self.init_weights()
        
    def init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv3d):
                nn.init.kaiming_normal_(m.weight,
                                        mode='fan_out',
                                        nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm3d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
        
        # Controllo delle dimensioni dei parametri
        # for p in self.parameters():
        #     print(p.size())
        
    def forward(self, node_features, edge_index, edge_weight, batch, return_embeddings=False):

        ###################################################################################
        # print(f"    - Inizio")
        # print(f"      node_features.shape (pre-forward): {node_features.shape}")
        # print(f"      node_features (pre-forward):       {node_features}")        # Questi coincidono esattamente con gli input
        # print("")
        ###################################################################################

        # Gli input vengono dati in pasto alla GCN
        node_features = super().forward(node_features, edge_index, edge_weight, batch)

        ###################################################################################
        # print(f"    - super().forward (GCN)")
        # print(f"      node_features.shape (post-forward): {node_features.shape}") # Corrisponde a ( return self.graph_convs[-1](node_features, batch) ) in src/utils/torch/gcn.py
        # print(f"      node_features (post-forward):       {node_features}")
        # print("")

        # print(f"    - self.downstream_layers (layer lineari finali)")             # Finisce con downstream_layers.append(nn.Linear(in_linear, self.n_classes))
        # print(f"      self.downstream_layers(node_features).shape: {self.downstream_layers(node_features).shape}")
        # print(f"      self.downstream_layers(node_features):       {self.downstream_layers(node_features)}")
        # print("")
        ###################################################################################

        if return_embeddings:
            graph_embeddings = node_features
            return self.downstream_layers(node_features), graph_embeddings

        return self.downstream_layers(node_features)
    
    def __init__downstream_layers(self):
        
        # initialize the linear layers interleaved with activation functions
        downstream_layers = []
        in_linear = self.out_channels

        for _ in range(self.num_dense_layers-1):
            downstream_layers.append(nn.Linear(in_linear, int(in_linear // self.linear_decay)))
            downstream_layers.append(nn.ReLU())
            in_linear = int(in_linear // self.linear_decay)

        # add the output layer
        downstream_layers.append(nn.Linear(in_linear, self.n_classes))
        #downstream_layers.append(nn.Sigmoid())
        #downstream_layers.append(nn.Softmax())
        
        # put the linear layers in sequential
        return nn.Sequential(*downstream_layers).double()
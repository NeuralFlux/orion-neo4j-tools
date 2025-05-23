from dataclasses import dataclass
from Common.biolink_constants import NAMED_THING
from Common.metadata import GraphMetadata, get_source_release_version
from Common.normalization import NormalizationScheme


class kgxnode:
    def __init__(self,
                 identifier,
                 name='',
                 categories=None,
                 nodeprops=None):
        self.identifier = identifier
        self.name = name
        self.categories = categories if categories else [NAMED_THING]
        self.properties = nodeprops if nodeprops else {}


class kgxedge:
    def __init__(self,
                 subject_id,
                 object_id,
                 predicate=None,
                 primary_knowledge_source=None,
                 aggregator_knowledge_sources: list = None,
                 edgeprops=None):
        self.subjectid = subject_id
        self.objectid = object_id
        self.predicate = predicate
        self.primary_knowledge_source = primary_knowledge_source
        self.aggregator_knowledge_sources = aggregator_knowledge_sources
        if edgeprops:
            self.properties = edgeprops
        else:
            self.properties = {}


@dataclass
class GraphSpec:
    graph_id: str
    graph_name: str
    graph_description: str
    graph_url: str
    graph_version: str
    graph_output_format: str
    sources: list = None
    subgraphs: list = None

    def get_metadata_representation(self):
        return {
            'graph_id': self.graph_id,
            'graph_name': self.graph_name,
            'graph_description': self.graph_description,
            'graph_url': self.graph_url,
            'graph_version': self.graph_version,
            'subgraphs': [subgraph.get_metadata_representation() for subgraph in self.subgraphs] if self.subgraphs else [],
            'sources': [source.get_metadata_representation() for source in self.sources] if self.sources else []
        }


@dataclass
class GraphSource:
    id: str
    merge_strategy: str = None
    edge_merging_attributes: list = None
    edge_id_addition: bool = False
    normalization_scheme: NormalizationScheme = None
    file_paths: list = None

    # Version may be generated when requested and differs for subclasses of GraphSource.
    def __getattribute__(self, name):
        if name == "version":
            return self.generate_version()
        else:
            return object.__getattribute__(self, name)

    def generate_version(self):
        return None

    def get_node_file_paths(self):
        if self.file_paths is None:
            raise Exception(f'File paths were requested before they were established for GraphSource {self.id}')
        return [file_path for file_path in self.file_paths if 'node' in file_path]

    def get_edge_file_paths(self):
        if self.file_paths is None:
            raise Exception(f'File paths were requested before they were established for GraphSource {self.id}')
        return [file_path for file_path in self.file_paths if 'edge' in file_path]


@dataclass
class SubGraphSource(GraphSource):
    graph_version: str = None
    graph_metadata: GraphMetadata = None

    def get_metadata_representation(self):
        return {'graph_id': self.id,
                'graph_version': self.graph_version,
                'merge_strategy:': self.merge_strategy,
                'graph_metadata': self.graph_metadata.metadata if self.graph_metadata else None}

    def generate_version(self):
        return self.graph_version


@dataclass
class DataSource(GraphSource):
    normalization_scheme: NormalizationScheme = None
    source_version: str = None
    parsing_version: str = None
    supplementation_version: str = None
    release_info: dict = None

    def get_metadata_representation(self):
        metadata = {'source_id': self.id,
                    'source_version': self.source_version,
                    'parsing_version': self.parsing_version,
                    'supplementation_version': self.supplementation_version,
                    'normalization_scheme': self.normalization_scheme.get_metadata_representation(),
                    'release_version': self.generate_version(),
                    'merge_strategy': self.merge_strategy,
                    'edge_merging_attributes': self.edge_merging_attributes,
                    'edge_id_addition': self.edge_id_addition}
        if self.release_info:
            metadata.update(self.release_info)
        return metadata

    # We can use generate_version to see if a source_version was already set. If not, we don't try to generate an
    # overall version because we can't. Typical usage would be a lazy instantiation approach, first setting
    # source_version to None, then checking this and retrieving/setting the source_version if needed,
    # after which the overall version can be generated.
    #
    # We use get_source_release_version to generate versions for data sources the same deterministic way that
    # the data source pipeline uses, so a version generated by a graph spec will match the release version generated by
    # previous runs of the pipeline.
    def generate_version(self):
        if self.source_version is None:
            return None
        return get_source_release_version(self.id,
                                          self.source_version,
                                          self.parsing_version,
                                          self.normalization_scheme.get_composite_normalization_version(),
                                          self.supplementation_version)

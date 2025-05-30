'''Instantiate knowledge graph object'''
from config.config import Config
from py2neo import Graph, NodeMatcher, RelationshipMatcher, ConnectionUnavailable

class GraphDao(object):

    def __init__(self):
        # Read yaml configuration
        self.__url = Config.get_instance().get_with_nested_params("database", "neo4j", "url")
        self.__username = Config.get_instance().get_with_nested_params("database", "neo4j", "username")
        self.__password = Config.get_instance().get_with_nested_params("database", "neo4j", "password")
        self.__connect_graph()

        # Create node matcher
        self.__node_matcher = NodeMatcher(self.__graph) if self.__graph else None

        # Create relationship matcher
        self.__relationship_matcher = RelationshipMatcher(self.__graph) if  self.__graph else None

    @staticmethod
    def ensure_connection(function):
        def wrapper(*args, **kwargs):
            if not args[0].__graph:
                return None
            return function(*args, **kwargs)

        return wrapper

    def __connect_graph(self):
        try:
            self.__graph = Graph(self.__url, auth=(self.__username, self.__password))
        except ConnectionUnavailable as e:
            self.__graph = None
    
    @ensure_connection
    def query_relationship_by_name(self, entity_name: str):
        # Write Cypher query to find all relationships where the specified entity is the starting or target node
        query = """
        MATCH (a)-[r]-(b)
        WHERE a.name = $entity_name
        RETURN a,r,b
        """
        # Execute query and return results
        result = self.__graph.run(query, entity_name=entity_name).data()
        return result
    
    @ensure_connection
    def query_node(self, *label, **properties):
        return self.__node_matcher.match(*label, **properties)

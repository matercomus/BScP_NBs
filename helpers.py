# SPARQL and GraphDB helper functions

import datetime
import time
import logging
import pandas as pd
import rdflib as rdflib
import requests

from typing import Any, Dict, Optional
from SPARQLWrapper import SPARQLWrapper
from pydantic import BaseModel, AnyUrl
from rdflib import Graph, URIRef
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore, Store

# set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


def get_timestamp_now():
    """
    Returns the current timestamp in ISO 8601 format.
    """
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()  # ISO 8601


def inject_binding_set_into_graph_pattern(graph_pattern: str, binding_set: list[dict[str, str]]) -> list[str]:
    """
    Injects a binding set into a graph pattern.

    :param graph_pattern: A string representing the graph pattern.
    :param binding_set: A list of dictionaries representing the binding set.
    :return: A list of strings representing the graph pattern with the binding set injected.
    """
    # check if the binding set is empty
    if binding_set in [None, []]:
        raise ValueError('binding_set cannot be empty')
    else:
        for binding in binding_set:
            for key, value in binding.items():
                graph_pattern = graph_pattern.replace('?' + key, value)
        # Remove < and > characters from GRAPH_PATTERN
        graph_pattern = graph_pattern.replace('<', '').replace('>', '')
        graph_pattern = graph_pattern.splitlines()
        graph_pattern = [line.strip() for line in graph_pattern if line.strip()]
        return graph_pattern


def replace_prefixes_with_uris(graph_pattern: list[str], prefixes: dict) -> list[str | Any]:
    """
    Replaces prefixes with URIs in a given graph pattern.

    :param graph_pattern: A list of strings representing the graph pattern.
    :param prefixes: A dictionary mapping prefixes to URIs.
    :return: A list of strings representing the graph pattern with prefixes replaced by URIs.
    """
    # check if the prefixes dictionary is empty
    if prefixes in [None, {}]:
        raise ValueError('prefixes cannot be empty')
    else:
        result = []
        for line in graph_pattern:
            for prefix, uri in prefixes.items():
                line = line.replace(prefix + ':', uri).replace('"', '')
            result.append(line)
        return result


def convert_to_turtle_rdf(graph_pattern: str, binding_set: list[dict[str, str]], prefixes: dict) -> str:
    """
    Converts a given graph pattern to Turtle RDF format.

    :param graph_pattern: A string representing the graph pattern.
    :param binding_set: A list of dictionaries representing the binding set.
    :param prefixes: A dictionary mapping prefixes to URIs.
    :return: A string representing the Turtle RDF format of the given graph pattern.
    """
    rdf = inject_binding_set_into_graph_pattern(graph_pattern, binding_set)
    rdf = replace_prefixes_with_uris(rdf, prefixes)
    result = []
    for line in rdf:
        subject, predicate, obj = line.split()[:3]
        if obj.startswith('http'):
            obj = f'<{obj}>'
        else:
            obj = f'"{obj}"'
        result.append(f'<{subject}> <{predicate}> {obj} .')
    return '\n'.join(result)


def set_store_header_update(store: Store):
    """
    Sets the appropriate request headers for update operations on a given store.

    :param store: The store object to set headers on.
    """
    
    """Call this function before any `Graph.add()` calls to set the appropriate request headers."""
    if 'headers' not in store.kwargs:
        store.kwargs.update({'headers': {}})
        store.kwargs['headers'].update({'content-type': 'application/sparql-update'})


def set_store_header_read(store: Store):
    """
    Sets the appropriate request headers for read operations on a given store.

    :param store: The store object to set headers on.
    """
    """Call this function before any `Graph.triples()` calls to set the appropriate request headers."""
    if 'headers' not in store.kwargs:
        store.kwargs.update({'headers': {}})
        store.kwargs['headers'].pop('content-type', None)


def store_data_in_graphdb(graph_pattern: str, binding_set: list[dict[str, str]],
                          prefixes: dict, read_url: str, write_url: str):
    """
    Store data in a graph database using the given graph pattern and binding set.

    :param graph_pattern: A string representing the graph pattern to use for storing the data.
    :param binding_set: A list of dictionaries representing the binding set to use for storing the data.
    :param prefixes: A dictionary of prefixes to use when converting the graph pattern to turtle RDF format.
    :param read_url: The URL of the SPARQL endpoint to use for reading data from the graph database.
    :param write_url: The URL of the SPARQL endpoint to use for writing data to the graph database.
    """
    turtle_rdf = convert_to_turtle_rdf(graph_pattern, binding_set, prefixes)
    store = SPARQLUpdateStore(query_endpoint=read_url, update_endpoint=write_url,
                              context_aware=True, postAsEncoded=False)
    store.debug = True
    store.method = 'POST'
    g = Graph(identifier=URIRef("http://example.org/mygraph"), store=store)
    g.parse(data=turtle_rdf, format="turtle")
    set_store_header_update(store)
    # TODO: fix this 500 error
    try:
        store.add_graph(g)
    except Exception as e:
        if hasattr(e, 'code') and e.code == 500:
            logging.debug("Ignoring 500 server error")
        else:
            raise e


def read_triples_from_graphdb(read_url: str, write_url: str):
    """
    Read triples from a graph database.

    :param read_url: The URL of the SPARQL endpoint to use for reading data from the graph database.
    :param write_url: The URL of the SPARQL endpoint to use for writing data to the graph database.
    :return: An iterator over the triples in the graph database.
    """
    store = SPARQLUpdateStore(query_endpoint=read_url, update_endpoint=write_url,
                              context_aware=True, postAsEncoded=False)
    store.debug = True
    store.method = 'POST'
    g = Graph(identifier=URIRef("http://example.org/mygraph"), store=store)
    # Read some triples.
    set_store_header_read(store)
    return g.triples((None, None, None))


def run_sparql_query(endpoint, query, return_format: str = "json"):
    """
    Run a SPARQL query against a given endpoint and return the results.

    :param endpoint: The URL of the SPARQL endpoint to query.
    :param query: The SPARQL query to run.
    :param return_format: The format in which to return the results (default is "json").
    :return: The results of the SPARQL query in the specified format.
    """
    sparql = SPARQLWrapper(endpoint)
    sparql.setQuery(query)
    sparql.setReturnFormat(return_format.lower())
    results = sparql.query().convert()
    return results


def sparql_results_to_df(results):
    """
    Convert SPARQL query results in JSON format into a pandas DataFrame.

    :param results: The result of a SPARQL query in JSON format.
    :return: A pandas DataFrame containing the data from the SPARQL query results.
    """
    

    cols = results['head']['vars']
    out = []
    for row in results['results']['bindings']:
        item = {}
        for c in cols:
            item[c] = row.get(c, {}).get('value')
        out.append(item)
    return pd.DataFrame(out)


def convert_sparql_results_to_graph(
        results: Dict,
        subject_var: Optional[str] = None,
        predicate_var: Optional[str] = None,
        object_var: Optional[str] = None
) -> rdflib.Graph:
    """
    Convert SPARQL query results in JSON format into an rdflib.Graph object.

    :param results: The result of a SPARQL query in JSON format.
    :param subject_var: The name of the variable to use as the subject of each triple.
    :param predicate_var: The name of the variable to use as the predicate of each triple.
    :param object_var: The name of the variable to use as the object of each triple.
    :return: An rdflib.Graph object containing the data from the SPARQL query results.
    """
    g = rdflib.Graph()
    if len(results["results"]["bindings"]) > 0:
        first_result = results["results"]["bindings"][0]
        variables = list(first_result.keys())
        if subject_var is None and len(variables) >= 1:
            subject_var = variables[0]
        if predicate_var is None and len(variables) >= 2:
            predicate_var = variables[1]
        if object_var is None and len(variables) >= 3:
            object_var = variables[2]
        for result in results["results"]["bindings"]:
            s = rdflib.URIRef(result[subject_var]["value"])
            p = rdflib.URIRef(result[predicate_var]["value"])
            if result[object_var]["type"] == "uri":
                o = rdflib.URIRef(result[object_var]["value"])
            else:
                o = rdflib.Literal(result[object_var]["value"])
            g.add((s, p, o))
    return g

def convert_graph_pattern_to_sparql(graph_pattern, prefixes):
    prefix_str = ""
    for prefix, uri in prefixes.items():
        prefix_str += f"PREFIX {prefix}: <{uri}>\n"
    query = f"{prefix_str}\nSELECT *\nWHERE {{\n{graph_pattern}\n}}"
    return query

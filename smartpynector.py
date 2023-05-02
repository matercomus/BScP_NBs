"""
This is a python wrapper for the Knowledge Engine Smart Connector REST API.
See https://gitlab.inesctec.pt/interconnect-public/knowledge-engine/-/blob/main/openapi-sc.yaml
"""

import datetime
import logging
from typing import Any

import requests
from pydantic import BaseModel, AnyUrl
from rdflib import Graph, URIRef
from rdflib.plugins.stores import sparqlstore

# set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


class SmartConnector(BaseModel):
    knowledgeBaseId: AnyUrl
    knowledgeBaseName: str
    knowledgeBaseDescription: str
    reasonerEnabled: bool


def get_timestamp_now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()  # ISO 8601


def check_request_status(r):
    if r.status_code == 200:
        logging.info('Request successful')
        logging.debug(r.text)
    else:
        logging.error('Error in request')
        logging.error(r.text)


def create_smart_connector(smart_connector_obj: SmartConnector, knowledge_engine_url: AnyUrl):
    """
    Create a new Smart Connector for the given Knowledge Base.
    :param smart_connector_obj: smart connector object
    :param knowledge_engine_url: url of the Knowledge Engine
    :return: response of the request
    """
    headers = {
        'Content-Type': 'application/json',
        'Knowledge-Base-Id': smart_connector_obj.knowledgeBaseId,
    }
    r = requests.post(knowledge_engine_url + '/sc', headers=headers, json=smart_connector_obj.dict())

    # check if the request was successful
    check_request_status(r)

    return r


# TODO: add support for other types of Knowledge Interactions
def register_knowledge_interaction(knowledge_interaction_type: str, knowledge_engine_url: AnyUrl, prefixes: dict,
                                   graph_pattern: str, headers: dict):
    # check if the knowledge_interaction_type is valid
    ki_types = ['AskKnowledgeInteraction', 'AnswerKnowledgeInteraction']
    if knowledge_interaction_type not in ki_types:
        raise ValueError('knowledge_interaction_type must be one of the following: ' + str(ki_types))

    # data of the Knowledge Interaction
    ki_data = {
        "knowledgeInteractionType": knowledge_interaction_type,
        "prefixes": prefixes,
        "graphPattern": graph_pattern,
    }

    r = requests.post(knowledge_engine_url + '/sc/ki', headers=headers, json=ki_data)

    # check if the request was successful
    check_request_status(r)

    # add the prefixes dictionary to the result dictionary
    result = r.json()
    result["prefixes"] = prefixes

    return result


def perform_ask_knowledge_interaction(knowledge_engine_url: AnyUrl, knowledge_base_id: AnyUrl,
                                      knowledge_interaction_id: AnyUrl, ask_data: list[dict[str, str]]):
    headers = {
        "Knowledge-Base-Id": knowledge_base_id,
        "Knowledge-Interaction-Id": knowledge_interaction_id,
    }

    r = requests.post(knowledge_engine_url + '/sc/ask', headers=headers, json=ask_data)

    # check if the request was successful
    check_request_status(r)

    return r


def perform_answer_knowledge_interaction(knowledge_engine_url: AnyUrl, knowledge_base_id: AnyUrl,
                                         knowledge_interaction_id: AnyUrl, answer_binding_set: list[dict[str, str]]):
    # get a handle request id
    handle_headers = {
        "Content-Type": "application/json",
        "Knowledge-Base-Id": knowledge_base_id,
    }
    # create a session with retries to avoid 202 errors
    # s = requests.Session()
    # retries = Retry(backoff_factor=1, status_forcelist=[i for i in range(202, 500)])
    # s.mount('https://', HTTPAdapter(max_retries=retries))

    # make the handle request
    handle_request = requests.get(knowledge_engine_url + '/sc/handle', headers=handle_headers, timeout=None)

    # check if the request was successful
    # check_request_status(handle_request)

    handle_request_id = handle_request.json()['handleRequestId']

    # answer the Knowledge Interaction
    answer_headers = {
        "Content-Type": "application/json",
        "Knowledge-Base-Id": knowledge_base_id,
        "Knowledge-Interaction-Id": knowledge_interaction_id,
    }
    answer_data = {
        "handleRequestId": handle_request_id,
        "bindingSet": answer_binding_set,
    }
    r = requests.post(knowledge_engine_url + '/sc/handle', headers=answer_headers, json=answer_data)
    # check if the request was successful
    # check_request_status(r)

    return r


def inject_binding_set_into_graph_pattern(graph_pattern: str, binding_set: list[dict[str, str]]) -> list[str]:
    for binding in binding_set:
        for key, value in binding.items():
            graph_pattern = graph_pattern.replace('?' + key, value)
    # Remove < and > characters from GRAPH_PATTERN
    graph_pattern = graph_pattern.replace('<', '').replace('>', '')
    graph_pattern = graph_pattern.splitlines()
    graph_pattern = [line.strip() for line in graph_pattern if line.strip()]
    return graph_pattern


def replace_prefixes_with_uris(graph_pattern: list[str], prefixes: dict) -> list[str | Any]:
    result = []
    for line in graph_pattern:
        for prefix, uri in prefixes.items():
            line = line.replace(prefix + ':', uri).replace('"', '')
        result.append(line)
    return result


def convert_to_turtle_rdf(graph_pattern: str, binding_set: list[dict[str, str]], prefixes: dict) -> str:
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


def save_graph_to_graphdb(graph, read_url: str, write_url: str):
    store = sparqlstore.SPARQLUpdateStore()
    store.open((read_url, write_url))
    store.add_graph(graph)


def store_data_in_graphdb(graph_pattern: str, binding_set: list[dict[str, str]],
                          prefixes: dict, read_url: str, write_url: str):
    turtle_rdf = convert_to_turtle_rdf(graph_pattern, binding_set, prefixes)
    g = Graph(identifier=URIRef("http://example.org/mygraph"))
    g.parse(data=turtle_rdf, format="turtle")
    g.print()
    save_graph_to_graphdb(g, read_url, write_url)

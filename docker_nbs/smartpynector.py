"""
This is a python wrapper for the Knowledge Engine Smart Connector REST API.
See https://gitlab.inesctec.pt/interconnect-public/knowledge-engine/-/blob/main/openapi-sc.yaml
"""

import datetime
import time
import logging
from typing import Any, Dict, Optional

import pandas as pd
import rdflib as rdflib
import requests
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


class SmartConnector(BaseModel):
    knowledgeBaseId: str
    knowledgeBaseName: str
    knowledgeBaseDescription: str
    reasonerEnabled: bool


def get_timestamp_now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()  # ISO 8601


def create_smart_connector(smart_connector_obj: SmartConnector, knowledge_engine_url: str):
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

    return r


def register_knowledge_interaction(knowledge_interaction_type: str, knowledge_engine_url: AnyUrl, prefixes: dict = None,
                                   graph_pattern: str = None, headers: dict = None, argument_graph_pattern: str = None,
                                   result_graph_pattern: str = None, ki_name: str = None, kb_id: str = None):
    # check if the knowledge_interaction_type is valid
    ki_types = ['AskKnowledgeInteraction', 'AnswerKnowledgeInteraction', "ReactKnowledgeInteraction", "PostKnowledgeInteraction"]
    if knowledge_interaction_type not in ki_types:
        raise ValueError('knowledge_interaction_type must be one of the following: ' + str(ki_types))

    # data of the Knowledge Interaction
    if knowledge_interaction_type in ['AskKnowledgeInteraction', 'AnswerKnowledgeInteraction']:
        ki_data = {
            "knowledgeInteractionName": ki_name,
            "knowledgeInteractionType": knowledge_interaction_type,
            "prefixes": prefixes,
            "graphPattern": graph_pattern,
        }
    elif knowledge_interaction_type == "ReactKnowledgeInteraction":
        ki_data = {
            "knowledgeInteractionName": ki_name,
            "knowledgeInteractionType": knowledge_interaction_type,
            "argumentGraphPattern": argument_graph_pattern,
            "resultGraphPattern": result_graph_pattern,
            "prefixes": prefixes,
        }
    elif knowledge_interaction_type == "PostKnowledgeInteraction":
        ki_data = {
            "knowledgeInteractionName": ki_name,
            "knowledgeInteractionType": knowledge_interaction_type,
            "argumentGraphPattern": argument_graph_pattern,
            "prefixes": prefixes,
        }
        if result_graph_pattern is not None:
            ki_data["argumentGraphPattern"] = result_graph_pattern
    else:
        raise ValueError('knowledge_interaction_type must be one of the following: ' + str(ki_types))

    r = requests.post(knowledge_engine_url + '/sc/ki', headers=headers, json=ki_data)

    # check if the request was successful
    assert r.ok

    return r


def perform_ask_knowledge_interaction(knowledge_engine_url: AnyUrl, knowledge_base_id: AnyUrl,
                                      knowledge_interaction_id: AnyUrl, ask_data: list[dict[str, str]]):
    headers = {
        "Knowledge-Base-Id": knowledge_base_id,
        "Knowledge-Interaction-Id": knowledge_interaction_id,
    }

    r = requests.post(knowledge_engine_url + '/sc/ask', headers=headers, json=ask_data)

    # check if the request was successful
    assert r.ok

    return r


def perform_answer_knowledge_interaction(knowledge_engine_url: AnyUrl, knowledge_base_id: AnyUrl,
                                         knowledge_interaction_id: AnyUrl, answer_binding_set: list[dict[str, str]]):
    while True:
        # get a handle request id
        handle_headers = {
            "Content-Type": "application/json",
            "Knowledge-Base-Id": knowledge_base_id,
        }

        # make the handle request
        handle_request = requests.get(knowledge_engine_url + '/sc/handle', headers=handle_headers, timeout=None)

        if handle_request.status_code == 200:
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

            if r.ok:
                return r
            else:
                logging.warn(f"received unexpected status {r.status_code}")
                logging.warn(r.text)
                logging.info("retrying after a short timeout")
                time.sleep(2)
                continue
        elif handle_request.status_code == 202:
            # 202 means: repoll (heartbeat)
            continue
        elif handle_request.status_code == 410:
            # 410 means: KE has stopped, so terminate
            break
        else:
            logging.warn(f"received unexpected status {handle_request.status_code}")
            logging.warn(handle_request.text)
            logging.info("retrying after a short timeout")
            time.sleep(2)
            continue

    logging.info(f"exiting perform_answer_knowledge_interaction")
    


    return response.json()["resultBindingSet"]


def start_handle_loop(handlers: dict[str, callable], kb_id: str, ke_endpoint: str):
    """
    Start the handle loop, where it will long poll to a route that returns a
    handle request when it arrives.

    Once a handle request is returns (on status 200) for an ANSWER/REACT, it
    will be handled by the corresponding knowledge interaction handler given in
    `handlers` (keyed by the knowledge interaction ID), and the result is passed
    back to the KE.
    """
    while True:
        response = requests.get(
            ke_endpoint + "sc/handle", headers={"Knowledge-Base-Id": kb_id}
        )

        if response.status_code == 200:
            # 200 means: we receive bindings that we need to handle, then repoll asap.
            handle_request = response.json()

            ki_id = handle_request["knowledgeInteractionId"]
            handle_request_id = handle_request["handleRequestId"]
            bindings = handle_request["bindingSet"]

            assert ki_id in handlers
            handler = handlers[ki_id]

            # pass the bindings to the handler, and let it handle them
            result_bindings = handler(bindings)

            handle_response = requests.post(
                ke_endpoint + "sc/handle",
                json={
                    "handleRequestId": handle_request_id,
                    "bindingSet": result_bindings,
                },
                headers={
                    "Knowledge-Base-Id": kb_id,
                    "Knowledge-Interaction-Id": ki_id,
                },
            )
            assert handle_response.ok

            continue
        elif response.status_code == 202:
            # 202 means: repoll (heartbeat)
            continue
        elif response.status_code == 410:
            # 410 means: KE has stopped, so terminate
            break
        else:
            logger.warn(f"received unexpected status {response.status_code}")
            logger.warn(response.text)
            logger.info("repolling after a short timeout")
            time.sleep(2)
            continue

    logger.info(f"exiting handle loop")



def inject_binding_set_into_graph_pattern(graph_pattern: str, binding_set: list[dict[str, str]]) -> list[str]:
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
    """Call this function before any `Graph.add()` calls to set the appropriate request headers."""
    if 'headers' not in store.kwargs:
        store.kwargs.update({'headers': {}})
    store.kwargs['headers'].update({'content-type': 'application/sparql-update'})


def set_store_header_read(store: Store):
    """Call this function before any `Graph.triples()` calls to set the appropriate request headers."""
    if 'headers' not in store.kwargs:
        store.kwargs.update({'headers': {}})
    store.kwargs['headers'].pop('content-type', None)


def store_data_in_graphdb(graph_pattern: str, binding_set: list[dict[str, str]],
                          prefixes: dict, read_url: str, write_url: str):
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
    store = SPARQLUpdateStore(query_endpoint=read_url, update_endpoint=write_url,
                              context_aware=True, postAsEncoded=False)
    store.debug = True
    store.method = 'POST'
    g = Graph(identifier=URIRef("http://example.org/mygraph"), store=store)
    # Read some triples.
    set_store_header_read(store)
    return g.triples((None, None, None))


def run_sparql_query(endpoint, query, return_format: str = "json"):
    sparql = SPARQLWrapper(endpoint)
    sparql.setQuery(query)
    sparql.setReturnFormat(return_format.lower())
    results = sparql.query().convert()
    return results


def sparql_results_to_df(results):
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

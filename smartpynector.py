'''
This is a python wrapper for the Knowledge Engine Smart Connector REST API.
See https://gitlab.inesctec.pt/interconnect-public/knowledge-engine/-/blob/main/openapi-sc.yaml
'''

import logging

import httpx
from pydantic import BaseModel, AnyUrl

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


def check_request_status(r):
    if r.status_code == 200:
        logging.info('Request successful')
    else:
        logging.error('Error in request')
        logging.error(r.text)


# TODO: FIX THIS
def register_ask_ki(knowledge_engine_url: AnyUrl, prefixes: dict, graph_pattern: str, headers: dict):
    # data for the AskKnowledgeInteraction
    ask_ki_data = {
        "knowledgeInteractionType": "AskKnowledgeInteraction",
        "prefixes": prefixes,
        "graphPattern": graph_pattern,
    }

    r = httpx.post(knowledge_engine_url + '/sc/ki', headers=headers, json=ask_ki_data)

    # check if the request was successful
    check_request_status(r)

    return r


def register_answer_ki(knowledge_engine_url: AnyUrl, prefixes: dict, graph_pattern: str, headers: dict):
    # data for the AnswerKnowledgeInteraction
    answer_ki_data = {
        "knowledgeInteractionType": "AnswerKnowledgeInteraction",
        "prefixes": prefixes,
        "graphPattern": graph_pattern,
    }

    r = httpx.post(knowledge_engine_url + '/sc/ki', headers=headers, json=answer_ki_data)

    # check if the request was successful
    check_request_status(r)
    return r


def register_knowledge_interaction(
        knowledge_engine_url: AnyUrl,
        knowledge_base_id: AnyUrl,
        knowledge_interaction_type: str,
        prefixes: dict,
        graph_pattern: str,
):
    """
    Register a Knowledge Interaction for a Smart Connector
    :param knowledge_engine_url: url of the Knowledge Engine
    :param knowledge_base_id: id of the Knowledge Base of the Smart Connector
    :param knowledge_interaction_type: type of Knowledge Interaction [AskKnowledgeInteraction,
                                                                        AnswerKnowledgeInteraction, more to come]
    :param prefixes: prefixes used in the graph pattern
    :param graph_pattern: the graph pattern of the Knowledge Interaction in SPARQL as a string
    :return: response of the request
    """
    headers = {
        'Content-Type': 'application/json',
        'Knowledge-Base-Id': knowledge_base_id,
    }

    if knowledge_interaction_type == 'AskKnowledgeInteraction':
        register_ask_ki(knowledge_engine_url, prefixes, graph_pattern, headers)

    elif knowledge_interaction_type == 'AnswerKnowledgeInteraction':
        register_answer_ki(knowledge_engine_url, prefixes, graph_pattern, headers)

    else:
        logging.error(f'Knowledge Interaction type {knowledge_interaction_type} not supported')
        return None


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
    r = httpx.post(knowledge_engine_url + '/sc', headers=headers, json=smart_connector_obj.dict())

    # check if the request was successful
    if r.status_code == 200:
        logging.info('Smart Connector created successfully')
    else:
        logging.error('Error creating Smart Connector')
        logging.error(r.text)

    return r

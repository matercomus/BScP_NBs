"""
This is a python wrapper for the Knowledge Engine Smart Connector REST API.
See https://gitlab.inesctec.pt/interconnect-public/knowledge-engine/-/blob/main/openapi-sc.yaml
"""

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
        logging.debug(r.text)
    else:
        logging.error('Error in request')
        logging.error(r.text)


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

    r = httpx.post(knowledge_engine_url + '/sc/ki', headers=headers, json=ki_data)

    # check if the request was successful
    check_request_status(r)

    return r


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
    check_request_status(r)

    return r

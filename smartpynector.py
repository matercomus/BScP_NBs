"""
This is a python wrapper for the Knowledge Engine Smart Connector REST API.
See https://gitlab.inesctec.pt/interconnect-public/knowledge-engine/-/blob/main/openapi-sc.yaml
"""

import datetime
import logging

import requests
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

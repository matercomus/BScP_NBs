'''
This is a python wrapper for the Knowledge Engine Smart Connector REST API.
See https://gitlab.inesctec.pt/interconnect-public/knowledge-engine/-/blob/main/openapi-sc.yaml
'''

import httpx
import logging
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

    def create_smart_connector(self, knowledge_engine_url: AnyUrl):
        """
        Create a new Smart Connector for the given Knowledge Base.
        :param knowledge_engine_url: url of the Knowledge Engine
        :return: response of the request
        """
        headers = {
            'Content-Type': 'application/json',
            'Knowledge-Base-Id': self.knowledgeBaseId,
        }
        r = httpx.post(knowledge_engine_url + '/sc', headers=headers, json=self.dict())

        if r.status_code == 200:
            logging.info('Smart Connector created successfully')
        else:
            logging.error('Error creating Smart Connector')
            logging.error(r.text)

        return r

    def register_knowledge_interaction(
            self,
            knowledge_engine_url: AnyUrl,
            knowledge_interaction_type: str,
            prefixes: dict,
            graph_pattern: str,
    ):
        """
        Register a Knowledge Interaction for a Smart Connector
        :param knowledge_engine_url: url of the Knowledge Engine
        :param knowledge_interaction_type: type of Knowledge Interaction [AskKnowledgeInteraction,
                                                                            AnswerKnowledgeInteraction, more to come]
        :param prefixes: prefixes used in the graph pattern
        :param graph_pattern: the graph pattern of the Knowledge Interaction in SPARQL as a string
        :return: response of the request
        """
        headers = {
            'Content-Type': 'application/json',
            'Knowledge-Base-Id': self.knowledgeBaseId,
        }

        if knowledge_interaction_type == 'AskKnowledgeInteraction':
            ask_ki_data = {
                "knowledgeInteractionType": "AskKnowledgeInteraction", }
            # TODO: add the rest of the AskKnowledgeInteraction data

        elif knowledge_interaction_type == 'AnswerKnowledgeInteraction':
            answer_ki_data = {
                "knowledgeInteractionType": "AnswerKnowledgeInteraction",
                "prefixes": prefixes,
                "graphPattern": graph_pattern,
            }

            r = httpx.post(knowledge_engine_url + '/sc/ki', headers=headers, json=answer_ki_data)

            if r.status_code == 200:
                logging.info('Knowledge Interaction registered successfully')
            else:
                logging.error('Error registering Knowledge Interaction')
                logging.error(r.text)
            return r

        else:
            logging.error(f'Knowledge Interaction type {knowledge_interaction_type} not supported')
            return None

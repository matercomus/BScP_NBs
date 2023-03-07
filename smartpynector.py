'''
This is a python wrapper for the Knowledge Engine REST API.
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
        Create a Smart Connector
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
        headers = {
            'Content-Type': 'application/json',
            'Knowledge-Base-Id': self.knowledgeBaseId,
        }

        if knowledge_interaction_type == 'AskKnowledgeInteraction':
            ask_ki_data = {
                "knowledgeInteractionType": "AskKnowledgeInteraction",}
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

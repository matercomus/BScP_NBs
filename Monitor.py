# This script is an intro into the Knowledge Engine REST Developer API
# see https://gitlab.inesctec.pt/interconnect-public/knowledge-engine/-/blob/main/openapi-sc.yaml

import httpx
import json
import re


# function for pretty printing JSON
def print_json(json_string):
    print(json.dumps(json.loads(json_string), indent=4))


# function for pretty printing RDF
def display_rdf_pattern(string):
    return re.sub(r'(\.\s)', r'\1\n', string)


# function summary of available Knowledge Interactions
def print_ki_summary(json_string):
    print_json(json_string)
    print()
    for ki in json.loads(json_string):
        print(ki['knowledgeInteractionName'])
        print('argumentGraphPattern')
        print(display_rdf_pattern(ki['argumentGraphPattern']))
        print('resultGraphPattern')
        print(display_rdf_pattern(ki['resultGraphPattern']))


# set the URL
URL = "https://ke.interconnectproject.eu/rest/"

# GET request /sc - Either get all available Smart Connectors or a specific one if the Knowledge-Base-Id is provided.
headers1 = {
    'accept': 'application/json; charset=UTF-8',
    'Knowledge-Base-Id': '',
}
# r = httpx.get(URL + "sc", headers=headers1)

# GET request /sc/ki - Get all KnowledgeInteractions for a given Knowledge-Base-Id
headers2 = {
    'accept': 'application/json; charset=UTF-8',
    'Knowledge-Base-Id': 'https://ke.interconnectproject.eu/adapter/evtd-kb',
}
r = httpx.get(URL + "sc/ki", headers=headers2)

print_ki_summary(r.text)

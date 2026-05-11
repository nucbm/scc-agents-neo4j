import json
import requests
from neo4j import GraphDatabase


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3:mini"  # sau "phi", dacă așa îl ai instalat


class EntityAgent:

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def setup_constraints(self):
        query = """
        CREATE CONSTRAINT entity_name_unique IF NOT EXISTS
        FOR (e:Entity)
        REQUIRE e.name IS UNIQUE
        """
        with self.driver.session() as session:
            session.run(query)

    def get_documents(self):
        query = """
        MATCH (d:Document)
        RETURN d.id AS id, d.title AS title, d.text AS text
        ORDER BY d.id
        """
        with self.driver.session() as session:
            return [dict(record) for record in session.run(query)]
        

    def call_ollama(self, text: str):
        prompt = f"""
Extract named entities from the text.

Allowed entity types:
- Organization
- Product
- Technology
- Platform
- Person
- Location
- Other

Return ONLY JSON.
No markdown.
No explanation.

Example:
{{
  "entities": [
    {{
        "name": "OpenAI", 
        "type": "Organization"
    }}
  ]
}}

Text:
{text}
"""

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format":"json"
            },
            timeout=120
        )

        response.raise_for_status()
        raw = response.json()["response"].strip()

        print("\nRAW MODEL OUTPUT:")
        print(raw)

        # remove markdown fences if present
        raw = raw.replace("```json", "")
        raw = raw.replace("```", "")
        raw = raw.strip()

        try:
            data = json.loads(raw)
            # sanitize malformed entities
            cleaned_entities = []
            for entity in data.get("entities", []):
                name = entity.get("name")

                # fallback repairs
                if not name:
                    name = entity.get("nameintext")

                if not name:
                    continue

                cleaned_entities.append({
                    "name": str(name).strip(),
                    "type": str(entity.get("type", "Other")).strip()
                })

            return {"entities": cleaned_entities} # json.loads(raw)
        except json.JSONDecodeError:
            print("Invalid JSON from model:")
            print(raw)
            return {"entities": []}
    


    def save_entities(self, doc_id: str, entities):
        query = """
        MATCH (d:Document {id: $doc_id})
        MERGE (e:Entity {name: $name})
        SET e.type = $type,
            e.created_by = 'EntityAgent'
        MERGE (d)-[:MENTIONS]->(e)
        RETURN e.name AS name, e.type AS type
        """

        with self.driver.session() as session:
            for entity in entities:
                name = entity.get("name")
                entity_type = entity.get("type", "Other")

                if not name:
                    continue

                result = session.run(
                    query,
                    doc_id=doc_id,
                    name=name,
                    type=entity_type
                )

                row = result.single()
                print(f"{doc_id} mentions entity: {row['name']} ({row['type']})")

    def run(self):
        print("Running Entity Agent...")
        self.setup_constraints()

        documents = self.get_documents()

        for doc in documents:
            print(f"\nProcessing {doc['id']}: {doc['title']}")
            result = self.call_ollama(doc["text"])
            entities = result.get("entities", [])
            self.save_entities(doc["id"], entities)

        print("\nEntity Agent finished.")


if __name__ == "__main__":
    agent = EntityAgent(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password"
    )

    try:
        agent.run()
    finally:
        agent.close()



import json
import requests
from neo4j import GraphDatabase


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3:mini"


class RelationAgent:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_documents_with_entities(self):
        query = """
        MATCH (d:Document)-[:MENTIONS]->(e:Entity)
        RETURN
            d.id AS id,
            d.title AS title,
            d.text AS text,
            collect(e.name) AS entities
        ORDER BY d.id
        """
        with self.driver.session() as session:
            return [dict(record) for record in session.run(query)]





    def call_ollama(self, text: str, entities):
        prompt = f"""
You extract relationships from text.

Use ONLY these entities:
{json.dumps(entities)}

Use ONLY these relation labels:
- develops
- provides
- invested_in
- integrates_into
- is_a
- used_by
- related_to

Return ONLY valid JSON.
No markdown.
No comments.
No extra fields.

Required JSON:
{{
  "relations": [
    {{
      "source": "OpenAI",
      "target": "ChatGPT",
      "relation": "provides",
      "confidence": 0.9
    }}
  ]
}}

If there are no relationships, return:
{{"relations": []}}

Text:
{text}
"""

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=120
        )

        response.raise_for_status()
        raw = response.json()["response"].strip()

        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            print("Invalid JSON from model:")
            print(raw)
            return {"relations": []}

        allowed_relations = {
            "develops",
            "provides",
            "invested_in",
            "integrates_into",
            "is_a",
            "used_by",
            "related_to",
        }

        cleaned = []

        for rel in data.get("relations", []):
            source = rel.get("source")
            target = rel.get("target")
            relation = rel.get("relation", "related_to")
            confidence = rel.get("confidence", 0.7)

            if source not in entities:
                continue

            if target not in entities:
                continue

            if relation not in allowed_relations:
                relation = "related_to"

            cleaned.append({
                "source": source,
                "target": target,
                "relation": relation,
                "confidence": float(confidence)
            })

        return {"relations": cleaned}






    def save_relations(self, doc_id: str, relations):
        query = """
        MATCH (source:Entity {name: $source})
        MATCH (target:Entity {name: $target})
        MERGE (source)-[r:RELATED_TO {
            relation: $relation,
            evidence_doc_id: $doc_id
        }]->(target)
        SET r.confidence = $confidence,
            r.created_by = 'RelationAgent'
        RETURN source.name AS source, r.relation AS relation, target.name AS target
        """

        with self.driver.session() as session:
            for rel in relations:
                source = rel.get("source")
                target = rel.get("target")
                relation = rel.get("relation")
                confidence = float(rel.get("confidence", 0.7))

                if not source or not target or not relation:
                    continue

                result = session.run(
                    query,
                    source=source,
                    target=target,
                    relation=relation,
                    confidence=confidence,
                    doc_id=doc_id
                )

                row = result.single()
                if row:
                    print(
                        f"{row['source']} -[{row['relation']}]-> {row['target']} "
                        f"(evidence: {doc_id})"
                    )



    def run(self):
        print("Running Relation Agent...")

        documents = self.get_documents_with_entities()

        for doc in documents:
            print(f"\nProcessing {doc['id']}: {doc['title']}")
            print(f"Entities: {doc['entities']}")

            result = self.call_ollama(
                text=doc["text"],
                entities=doc["entities"]
            )

            relations = result.get("relations", [])
            self.save_relations(doc["id"], relations)

        print("\nRelation Agent finished.")


if __name__ == "__main__":
    agent = RelationAgent(
        uri="bolt://localhost:7687",
        user="neo4j",
        password=""
    )

    try:
        agent.run()
    finally:
        agent.close()




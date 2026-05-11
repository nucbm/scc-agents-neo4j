import requests
from neo4j import GraphDatabase


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3:mini"


class QAAgent:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_graph_context(self):
        query = """
        MATCH (a:Entity)-[r:RELATED_TO]->(b:Entity)
        OPTIONAL MATCH (d:Document {id: r.evidence_doc_id})
        RETURN
            a.name AS source,
            r.relation AS relation,
            b.name AS target,
            r.confidence AS confidence,
            r.evidence_doc_id AS doc_id,
            d.title AS doc_title,
            d.text AS evidence_text
        ORDER BY doc_id
        """
        with self.driver.session() as session:
            return [dict(record) for record in session.run(query)]

    def call_ollama(self, question: str, facts):
        facts_text = "\n".join(
            [
                f"- {f['source']} --{f['relation']}--> {f['target']} "
                f"(source: {f['doc_id']}, evidence: {f['evidence_text']})"
                for f in facts
            ]
        )

        prompt = f"""
Answer the question using ONLY the facts below.

Rules:
- If the answer is not in the facts, say you do not know.
- Mention the document ids used as sources.
- Keep the answer short.
- Answer in Romanian.

Facts:
{facts_text}

Question:
{question}
"""

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )

        response.raise_for_status()
        return response.json()["response"].strip()

    def run(self, question: str):
        print("Running QA Agent...\n")

        facts = self.get_graph_context()

        if not facts:
            return "Nu am găsit relații în graf. Rulează mai întâi Relation Agent."

        answer = self.call_ollama(question, facts)

        print("Question:")
        print(question)
        print("\nAnswer:")
        print(answer)

        return answer


if __name__ == "__main__":
    agent = QAAgent(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password"
    )

    try:
        agent.run(
            "Ce relație există între Microsoft, OpenAI și Azure?"
        )
    finally:
        agent.close()



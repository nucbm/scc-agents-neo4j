from neo4j import GraphDatabase


DOCUMENTS = [
    {
        "id": "doc1",
        "title": "OpenAI and ChatGPT",
        "text": "OpenAI develops AI models and provides the ChatGPT product."
    },
    {
        "id": "doc2",
        "title": "Microsoft and Azure",
        "text": "Microsoft invested in OpenAI and integrates AI features into Azure."
    },
    {
        "id": "doc3",
        "title": "Azure cloud platform",
        "text": "Azure is a cloud platform used by enterprise developers."
    }
]


class DocumentAgent:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def setup_constraints(self):
        query = """
        CREATE CONSTRAINT document_id_unique IF NOT EXISTS
        FOR (d:Document)
        REQUIRE d.id IS UNIQUE
        """

        with self.driver.session() as session:
            session.run(query)

    def insert_documents(self, documents):
        query = """
        MERGE (d:Document {id: $id})
        SET d.title = $title,
            d.text = $text,
            d.created_by = 'DocumentAgent'
        RETURN d.id AS id, d.title AS title
        """

        with self.driver.session() as session:
            for doc in documents:
                result = session.run(
                    query,
                    id=doc["id"],
                    title=doc["title"],
                    text=doc["text"]
                )

                row = result.single()
                print(f"Inserted document: {row['id']} - {row['title']}")

    def run(self):
        print("Running Document Agent...")
        self.setup_constraints()
        self.insert_documents(DOCUMENTS)
        print("Document Agent finished.")


if __name__ == "__main__":
    agent = DocumentAgent(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password"
    )

    try:
        agent.run()
    finally:
        agent.close()



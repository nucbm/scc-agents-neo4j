from document_agent import DocumentAgent
from entity_agent import EntityAgent
from relation_agent import RelationAgent
from qa_agent import QAAgent


NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"


def main():
    print("\n=== Multi-Agent Knowledge Graph Demo ===\n")

    document_agent = DocumentAgent(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    entity_agent = EntityAgent(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    relation_agent = RelationAgent(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    qa_agent = QAAgent(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    try:
        document_agent.run()
        print("\n---\n")

        entity_agent.run()
        print("\n---\n")

        relation_agent.run()
        print("\n---\n")

        question = "Ce relație există între Microsoft, OpenAI și Azure?"
        qa_agent.run(question)

    finally:
        document_agent.close()
        entity_agent.close()
        relation_agent.close()
        qa_agent.close()


if __name__ == "__main__":
    main()



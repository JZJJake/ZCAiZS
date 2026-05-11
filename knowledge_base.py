import os
import sqlite3
import json
import uuid
import re
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
from openai import OpenAI

class KnowledgeBase:
    def __init__(self, data_dir="data", models_dir="models"):
        self.data_dir = data_dir
        self.models_dir = models_dir

        os.makedirs(self.data_dir, exist_ok=True)

        # Init ChromaDB
        self.chroma_client = PersistentClient(path=os.path.join(self.data_dir, "chroma_db"))
        self.collection = self.chroma_client.get_or_create_collection(name="policy_qa")

        # Init SQLite for Knowledge Graph
        self.db_path = os.path.join(self.data_dir, "graph.db")
        self._init_sqlite()

        # Load local embedding model
        model_path = os.path.join(self.models_dir, "text2vec-base-chinese")
        if os.path.exists(model_path):
            print(f"Loading local embedding model from {model_path}...")
            self.embedding_model = SentenceTransformer(model_path)
        else:
            print("Local embedding model not found. Using default online model (for demo purposes).")
            # Fallback for dev if user didn't run download_model.py
            self.embedding_model = SentenceTransformer("shibing624/text2vec-base-chinese")

        # Init DeepSeek Client (API key should be set in environment variable DEEPSEEK_API_KEY)
        self.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
        if self.deepseek_api_key:
            self.llm_client = OpenAI(
                api_key=self.deepseek_api_key,
                base_url="https://api.deepseek.com"
            )
        else:
            self.llm_client = None
            print("Warning: DEEPSEEK_API_KEY environment variable not set. Graph extraction and QA will not work properly.")

    def _init_sqlite(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE,
                type TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                source_id TEXT,
                target_id TEXT,
                relation TEXT,
                FOREIGN KEY(source_id) REFERENCES entities(id),
                FOREIGN KEY(target_id) REFERENCES entities(id)
            )
        ''')
        conn.commit()
        conn.close()

    def parse_markdown(self, filepath):
        """Parse markdown file and return a list of (question, answer) tuples."""
        qa_pairs = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split by double newlines or similar to get blocks
            blocks = re.split(r'\n\s*\n', content)

            current_q = None
            current_a = None

            for block in blocks:
                block = block.strip()
                if not block:
                    continue

                # Check if it contains both Q and A in one block
                if block.startswith("问：") and "答：" in block:
                    parts = block.split("答：", 1)
                    q = parts[0].replace("问：", "").strip()
                    a = parts[1].strip()
                    qa_pairs.append((q, a))
                elif block.startswith("问："):
                    current_q = block.replace("问：", "").strip()
                elif block.startswith("答：") and current_q is not None:
                    current_a = block.replace("答：", "").strip()
                    qa_pairs.append((current_q, current_a))
                else:
                    # Append to current answer if any
                    if current_a is not None:
                        current_a += "\n" + block
                        # Update the last pair
                        if qa_pairs:
                           qa_pairs[-1] = (qa_pairs[-1][0], current_a)

        except Exception as e:
            print(f"Error parsing markdown {filepath}: {e}")

        return qa_pairs

    def get_embeddings(self, texts):
        """Get embeddings using the local model."""
        embeddings = self.embedding_model.encode(texts)
        return embeddings.tolist()

    def add_to_vector_db(self, qa_pairs):
        """Add QA pairs to ChromaDB."""
        if not qa_pairs:
            return 0

        documents = []
        metadatas = []
        ids = []

        for q, a in qa_pairs:
            # We embed the combination of Q and A for better retrieval
            doc = f"问：{q}\n答：{a}"
            documents.append(doc)
            metadatas.append({"question": q, "answer": a})
            ids.append(str(uuid.uuid4()))

        embeddings = self.get_embeddings(documents)

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        return len(ids)

    def extract_graph_data(self, qa_pairs):
        """Extract entities and relationships using DeepSeek."""
        if not self.llm_client:
            print("Cannot extract graph data: No DeepSeek API Key.")
            return

        for q, a in qa_pairs:
            prompt = f"""
            分析以下政策问答，提取其中的核心实体和关系。
            实体(Entity)包括：机构、政策名词、条件、数字指标、资格等。
            关系(Relationship)描述实体间的联系，例如：包含、需要满足、属于、享受等。

            请返回JSON格式，格式严格如下：
            {{
                "entities": [
                    {{"name": "实体名称", "type": "实体类型"}}
                ],
                "relationships": [
                    {{"source": "源实体名称", "target": "目标实体名称", "relation": "关系描述"}}
                ]
            }}

            问答内容：
            问：{q}
            答：{a}
            """
            try:
                response = self.llm_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个专业的政策分析师和知识图谱提取工具。"},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )

                content = response.choices[0].message.content
                data = json.loads(content)
                self._save_graph_data(data)

            except Exception as e:
                print(f"Error extracting graph data for '{q}': {e}")

    def _save_graph_data(self, data):
        """Save extracted entities and relationships to SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        entity_name_to_id = {}

        for ent in data.get("entities", []):
            name = ent.get("name")
            e_type = ent.get("type", "Unknown")
            if not name: continue

            # Check if exists
            cursor.execute("SELECT id FROM entities WHERE name=?", (name,))
            row = cursor.fetchone()
            if row:
                entity_name_to_id[name] = row[0]
            else:
                e_id = str(uuid.uuid4())
                cursor.execute("INSERT INTO entities (id, name, type) VALUES (?, ?, ?)", (e_id, name, e_type))
                entity_name_to_id[name] = e_id

        for rel in data.get("relationships", []):
            source = rel.get("source")
            target = rel.get("target")
            relation = rel.get("relation")

            if source in entity_name_to_id and target in entity_name_to_id:
                s_id = entity_name_to_id[source]
                t_id = entity_name_to_id[target]
                r_id = str(uuid.uuid4())
                cursor.execute("INSERT INTO relationships (id, source_id, target_id, relation) VALUES (?, ?, ?, ?)",
                               (r_id, s_id, t_id, relation))

        conn.commit()
        conn.close()

    def process_file(self, filepath):
        """End-to-end processing of a markdown file."""
        qa_pairs = self.parse_markdown(filepath)
        count = self.add_to_vector_db(qa_pairs)
        # Optionally extract graph data asynchronously in a real app, here we do it synchronously
        self.extract_graph_data(qa_pairs)
        return count

    def get_graph_data(self):
        """Retrieve graph data for visualization."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, type FROM entities")
        entities = [{"id": r[0], "label": r[1], "group": r[2]} for r in cursor.fetchall()]

        cursor.execute("SELECT source_id, target_id, relation FROM relationships")
        edges = [{"from": r[0], "to": r[1], "label": r[2]} for r in cursor.fetchall()]

        conn.close()
        return {"nodes": entities, "edges": edges}

    def clear_database(self):
        """Clear both ChromaDB and SQLite."""
        # Clear ChromaDB
        docs = self.collection.get()
        if docs and docs['ids']:
            self.collection.delete(ids=docs['ids'])

        # Clear SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM relationships")
        cursor.execute("DELETE FROM entities")
        conn.commit()
        conn.close()

    def get_stats(self):
        """Get database statistics."""
        doc_count = self.collection.count()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entities")
        node_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM relationships")
        edge_count = cursor.fetchone()[0]
        conn.close()

        return {
            "documents": doc_count,
            "nodes": node_count,
            "edges": edge_count
        }

    def query(self, user_query, top_k=3):
        """RAG pipeline: Query DB and generate answer using DeepSeek."""
        # 1. Retrieve
        query_embedding = self.get_embeddings([user_query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        context_docs = results['documents'][0] if results['documents'] else []
        context_text = "\n\n".join(context_docs)

        if not context_text:
            return "知识库中没有找到相关信息。"

        # 2. Generate
        if not self.llm_client:
             return f"找到相关内容，但未配置DeepSeek API Key无法生成完整回答。\n\n参考内容：\n{context_text}"

        prompt = f"""
        你是一个专业的政策解答AI助手。请根据以下提供的政策知识库内容，回答用户的问题。
        如果知识库内容不能完全回答问题，请说明。

        【政策知识库内容】
        {context_text}

        【用户问题】
        {user_query}
        """

        try:
            response = self.llm_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的政策解答AI助手。"},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"生成回答时发生错误: {e}"

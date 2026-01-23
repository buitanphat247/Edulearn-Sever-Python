import os
import io
import json
import re
import concurrent.futures
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple
from werkzeug.datastructures import FileStorage
from openai import OpenAI

from src.services.exam_generation_service.document_service import DocumentService

import logging

# Suppress annoying pypdf warnings
logging.getLogger("pypdf").setLevel(logging.ERROR)

# LlamaIndex Imports
try:
    from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, Document, StorageContext, load_index_from_storage
    from llama_index.llms.openai import OpenAI as LlamaOpenAI
    from llama_index.llms.ollama import Ollama
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.core.node_parser import SentenceSplitter
    HAS_LLAMA_INDEX = True
except ImportError:
    HAS_LLAMA_INDEX = False
    print("⚠ LlamaIndex Core not installed.")

try:
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    HAS_HF_EMBEDDING = True
except ImportError:
    HAS_HF_EMBEDDING = False
    print("⚠ LlamaIndex HuggingFace Embedding not installed.")


class QuestionService:
    DEFAULT_MODE = "online"
    ONLINE_MODEL = "gpt-4o-mini"
    OFFLINE_MODEL = "qwen2.5:3b"

    def __init__(self):
        self.document_service = DocumentService()
        
    def _get_llm_client(self, mode: str = "online") -> Tuple[OpenAI, str]:
        """Trả về tuple (client, model_name) dựa trên mode"""
        if mode == "offline":
            # Config cho Local LLM (Ollama)
            base_url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
            api_key = "ollama"  # Dummy key
            model = self.OFFLINE_MODEL
            print(f"           [Mode: OFFLINE] Using Local LLM ({model}) at {base_url}")
            return OpenAI(base_url=base_url, api_key=api_key), model
        else:
            # Config cho Online LLM (OpenAI)
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found for online mode")
            
            model = os.getenv("OPENAI_MODEL", self.ONLINE_MODEL)
            print(f"           [Mode: ONLINE] Using OpenAI ({model})")
            return OpenAI(api_key=api_key), model
    
    def create_test_from_file(self, file: FileStorage, title: str, description: str, 
                              duration_minutes: int, total_score: int,
                              num_questions: int = 10, difficulty: str = "medium", mode: str = "llamaindex", 
                              class_id: int = None, max_attempts: int = 1, teacher_id: int = None) -> Dict:
        """Create a full Test from file content or description"""
        
        # Unified Pipeline (LlamaIndex)
        if not file:
            # Create dummy file from description if no file provided
            dummy_content = f"Instruction: {description}\nTopic: {title}\n".encode('utf-8')
            file = FileStorage(stream=io.BytesIO(dummy_content), filename="generated_topic.txt")
        
        print("\n" + "=" * 70)
        print("  START CREATING TEST (LLAMAINDEX PIPELINE)")
        print(f"  Title: {title}")
        print(f"  Mode: {mode}")
        print("=" * 70)
        
        # Determine backend mode
        backend_mode = "offline" if "offline" in mode.lower() else "online"
        
        file.seek(0)
        return self._generate_with_llamaindex(
            file=file, 
            num_questions=num_questions,
            title=title,
            description=description,
            difficulty=difficulty,
            duration_minutes=duration_minutes,
            total_score=total_score,
            mode_backend=backend_mode,
            class_id=class_id,
            max_attempts=max_attempts,
            teacher_id=teacher_id
        )

    def _generate_with_llamaindex(self, file: FileStorage, num_questions: int, 
                                  title: str, description: str, duration_minutes: int, total_score: int,
                                  difficulty: str = "medium", mode_backend: str = "online", 
                                  class_id: int = None, max_attempts: int = 1, teacher_id: int = None) -> Dict:
        """Sử dụng LlamaIndex để generate câu hỏi (RAG + Structured Output)"""
        start_time = datetime.now()
        print(f"\n⚡ [LlamaIndex] Starting generation pipeline...")
        
        # 1. Setup File
        temp_dir = "temp_processing"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        temp_file_path = os.path.join(temp_dir, file.filename)
        file.seek(0)
        file.save(temp_file_path)
        
        try:
            # 2. Load Documents
            documents = SimpleDirectoryReader(input_files=[temp_file_path]).load_data()
            print(f"     ✓ Loaded {len(documents)} document pages/sections")
            
            # 3. Create Document Record in DB (First!)
            doc_id = self.document_service.create_document(name=file.filename, status="processing")

            # 4. Explicit Chunking (Node Parsing) - Optimized Size
            parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)
            nodes = parser.get_nodes_from_documents(documents)
            
            print(f"     [LlamaIndex] Split content into {len(nodes)} chunks (nodes).")
            
            # 5. Save Chunks to Postgres (Simulate Vector DB Storage)
            chunks_data = []
            for i, node in enumerate(nodes):
                chunks_data.append({
                    "chunk_index": i + 1,
                    "text": node.text
                })
            
            # Save visible chunks for user inspection
            chunk_ids = self.document_service.create_chunks(doc_id, chunks_data)
            
            # 6. Configure LLM & Embeddings
            # A. Embedding Configuration (Shared for consistency & caching)
            if HAS_HF_EMBEDDING:
                print(f"     [Config] Using Local Embedding (sentence-transformers/all-MiniLM-L6-v2)")
                # Use the same model for both Online/Offline to allow Cache Sharing
                Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
            else:
                print(f"     [Config] Local Embedding not found. Fallback to OpenAI Embedding.")
                Settings.embed_model = OpenAIEmbedding()

            # B. LLM Configuration (The ONLY difference)
            if mode_backend == "offline":
                local_url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434")
                print(f"     [Config] Using Ollama (qwen2.5:3b) at {local_url}")
                try:
                    # Ensure base_url is clean
                    Settings.llm = Ollama(model="qwen2.5:3b", request_timeout=360.0, base_url=local_url)
                except Exception as e:
                     raise ValueError(f"Failed to config Ollama: {str(e)}")
            else:
                print(f"     [Config] Using OpenAI (gpt-4o-mini)")
                Settings.llm = LlamaOpenAI(model="gpt-4o-mini", temperature=0.3)
            
            # 7. Create/Load Index with ChromaDB (Local Vector DB)
            try:
                from llama_index.vector_stores.chroma import ChromaVectorStore
                import chromadb
            except ImportError:
                 raise ValueError("Please run: pip install llama-index-vector-stores-chroma chromadb")

            # Calculate Hash for Collection Name
            with open(temp_file_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            collection_name = f"doc_{file_hash}"
            
            # Init ChromaDB Client (Persistent Local Storage)
            chroma_path = "./storage_chroma"
            print(f"     [Chroma] Connecting to Local DB at {chroma_path} ... Collection: {collection_name}")
            db = chromadb.PersistentClient(path=chroma_path)
            
            # Get or Create Collection
            chroma_collection = db.get_or_create_collection(collection_name)
            
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            
            # Check if collection has data (Count items)
            if chroma_collection.count() > 0:
                print(f"     [Chroma] Found {chroma_collection.count()} vectors in cache! Loading index...")
                index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
            else:
                print(f"     [Chroma] New document. creating index & embedding...")
                storage_context = StorageContext.from_defaults(vector_store=vector_store)
                index = VectorStoreIndex(nodes, storage_context=storage_context)

            
            # OPTIMIZATION: compact response (saves tokens) + limit context (saves tokens)
            query_engine = index.as_query_engine(response_mode="compact", similarity_top_k=3)
            
            # 8. Generate Questions (Parallel Batches for Speed)
            batch_size = 5
            total_batches = (num_questions + batch_size - 1) // batch_size
            
            print(f"     [Gen] Parallelizing: {total_batches} batches of ~{batch_size} questions...")
            
            def generate_batch(count, batch_index):
                batch_prompt = f"""
                Task: Generate exactly {count} multiple choice questions (Vietnamese) from the context.
                Focus: Batch {batch_index} (ensure unique questions).
                Difficulty: {difficulty}
                Instruction: {description}
                
                Output Compressed JSON:
                [
                    {{
                        "q": "Question text",
                        "o": ["OptionA", "OptionB", "OptionC", "OptionD"],
                        "a": "A",
                        "e": "Short explanation"
                    }}
                ]
                """
                try:
                    resp = query_engine.query(batch_prompt)
                    # Parse JSON immediately
                    json_text = str(resp)
                    import re
                    import json
                    match = re.search(r'\[.*\]', json_text, re.DOTALL)
                    if match:
                        return json.loads(match.group(0))
                except Exception as ex:
                    print(f"     [Err] Batch {batch_index} failed: {ex}")
                return []

            final_questions = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                remaining = num_questions
                for i in range(total_batches):
                    count = min(batch_size, remaining)
                    futures.append(executor.submit(generate_batch, count, i+1))
                    remaining -= count
                
                for f in concurrent.futures.as_completed(futures):
                    batch_res = f.result()
                    if isinstance(batch_res, list):
                        final_questions.extend(batch_res)
            
            print(f"     [Gen] Combined results: {len(final_questions)} raw questions.")
            
            # Trim to exact limit
            if len(final_questions) > num_questions:
                final_questions = final_questions[:num_questions]
            
            # 9. Save to DB (Use existing doc_id from Step 3)
            self.document_service.update_document_status(doc_id, "indexed")
            
            test_id = self.document_service.create_test(
                title=title,
                description=description,
                document_id=doc_id,
                num_questions=len(final_questions),
                difficulty=difficulty,
                duration_minutes=duration_minutes,
                total_score=total_score,
                class_id=class_id,
                max_attempts=max_attempts,
                teacher_id=teacher_id
            )
            
            score_per_q = total_score // max(1, len(final_questions))
            saved_questions = []
            
            for idx, q_data in enumerate(final_questions):
                # Standardize keys from short format
                q_text = q_data.get("q") or q_data.get("question")
                options = q_data.get("o") or q_data.get("options") or [
                    q_data.get("answer_a"), q_data.get("answer_b"), q_data.get("answer_c"), q_data.get("answer_d")
                ]
                correct = q_data.get("a") or q_data.get("correct_answer") or "A"
                explanation = q_data.get("e") or q_data.get("explanation") or ""
                
                # Shuffle Options Logic
                opts = []
                # Ensure options is list of 4
                if isinstance(options, list):
                    while len(options) < 4: options.append("...")
                    for i, txt in enumerate(options[:4]):
                        opts.append({"txt": str(txt), "key": chr(65+i)})
                
                # Determine correct index
                c_char = str(correct).upper().strip()
                if c_char not in ['A', 'B', 'C', 'D']: c_char = 'A'
                
                # Mark IS_CORRECT based on original position (A=0, B=1...)
                c_idx = ord(c_char) - 65
                if c_idx < 0 or c_idx > 3: c_idx = 0
                
                option_objects = []
                for i, txt in enumerate(options[:4]):
                     option_objects.append({"txt": str(txt), "is_correct": (i == c_idx)})

                # Shuffle
                import random
                random.shuffle(option_objects)
                
                # Re-assign
                final_a = option_objects[0]["txt"]
                final_b = option_objects[1]["txt"]
                final_c = option_objects[2]["txt"]
                final_d = option_objects[3]["txt"]
                
                # Find new correct char
                new_correct_char = 'A'
                for i, obj in enumerate(option_objects):
                    if obj.get("is_correct"):
                        new_correct_char = chr(65 + i)
                        break

                q_id = self.document_service.create_question(
                    document_id=doc_id,
                    chunk_id=chunk_ids[idx % len(chunk_ids)] if chunk_ids else None,
                    content=q_text,
                    answer_a=final_a,
                    answer_b=final_b,
                    answer_c=final_c,
                    answer_d=final_d,
                    correct_answer=new_correct_char,
                    explanation=explanation
                )
                
                self.document_service.add_question_to_test(test_id, q_id, score=score_per_q, order=idx+1)
                
                # Optimize Response Object: Use only short keys, remove redundancy
                clean_item = {
                    "id": q_id,
                    "q": q_text,
                    "o": [final_a, final_b, final_c, final_d],
                    "a": new_correct_char,
                    "e": explanation
                }
                saved_questions.append(clean_item)
                
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"     ✓ LlamaIndex Pipeline Completed in {elapsed:.2f}s")
            
            return {
                "test_id": test_id,
                "title": title,
                "document_id": doc_id,
                "total_questions": len(saved_questions),
                "execution_time": f"{elapsed:.2f}s",
                "questions": saved_questions
            }
            
        except Exception as e:
            print(f"LlamaIndex Error: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            if os.path.exists(temp_file_path):
                try: os.remove(temp_file_path)
                except: pass

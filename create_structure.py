import os

# Define the folder and file structure
structure = {
    "app": {
        "__init__.py": "",
        "main.py": "# FastAPI main application\n",
        "routers": {
            "__init__.py": "",
            "chat_router.py": "# Chat endpoints\n",
            "admin_router.py": "# Admin endpoints for document management\n"
        },
        "core": {
            "__init__.py": "",
            "config.py": "# Application configuration\n",
            "security.py": "# Authentication and authorization\n"
        },
        "services": {
            "__init__.py": "",
            "document_service.py": "# Document processing\n",
            "chat_service.py": "# Chat processing\n",
            "llm_service.py": "# LLM integration\n"
        },
        "models": {
            "__init__.py": "",
            "database.py": "# Database models\n",
            "schemas.py": "# Pydantic schemas\n"
        },
        "utils": {
            "__init__.py": "",
            "embeddings.py": "# Embedding utilities\n",
            "vectorstore.py": "# Vector store management\n",
            "chunking.py": "# Text chunking utilities\n"
        }
    },
    "data": {
        "colleges": {
            "college_001": {
                "documents": {},
                "images": {},
                "vectorstore": {}
            },
            "college_002": {
                "documents": {},
                "images": {},
                "vectorstore": {}
            }
        }
    },
    "requirements.txt": "",
    "README.md": ""
}


def create_structure(base_path, struct):
    for name, content in struct.items():
        path = os.path.join(base_path, name)
        if isinstance(content, dict):
            os.makedirs(path, exist_ok=True)
            create_structure(path, content)
        else:
            # Create file and optionally write boilerplate content
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)


if __name__ == "__main__":
    current_dir = os.getcwd()
    create_structure(current_dir, structure)
    print("Project structure created successfully.")

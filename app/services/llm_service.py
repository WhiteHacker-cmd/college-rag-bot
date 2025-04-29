# LLM integration

# app/services/llm_service.py
# import os
# import json
# from typing import List, Dict, Any, Optional
# import logging
# from langchain.schema import SystemMessage, HumanMessage
# from langchain_community.llms import Ollama
# from langchain.chains import LLMChain
# from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain.memory import ConversationBufferMemory
# from app.core.config import settings

# logger = logging.getLogger(__name__)

# class LLMService:
#     def __init__(self):
#         """Initialize the LLM service with Ollama"""
#         try:
#             self.llm = Ollama(
#                 model=settings.LLM_MODEL,
#                 base_url=settings.OLLAMA_BASE_URL,
#                 temperature=0.7,
#                 top_k=40,
#                 top_p=0.9,
#                 repeat_penalty=1.1
#             )
#             logger.info(f"Initialized Ollama LLM with model {settings.LLM_MODEL}")
#         except Exception as e:
#             logger.error(f"Error initializing Ollama LLM: {str(e)}")
#             raise
    
#     def create_chat_prompt(self, college_name: str) -> ChatPromptTemplate:
#         """Create a chat prompt template for the college-specific assistant"""
#         system_template = f"""You are a helpful assistant for {college_name}. 
# Your goal is to provide accurate, helpful, and friendly responses to questions about the college.
# When answering questions, use the context provided to you. If the answer cannot be found in the context,
# politely state that you don't have that specific information but provide related information if available.

# Important: Provide natural responses without referring to document numbers or mentioning which specific document 
# information comes from. Simply present the information as if you know it directly. Do not use phrases like 
# "According to Document X" or "As mentioned in Document Y." Present information in a conversational, helpful tone
# that doesn't reveal the underlying document structure.

# For questions about images or visual elements, you can mention relevant images without referencing their numbers,
# describing what they show if appropriate.
# """
        
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", system_template),
#             MessagesPlaceholder(variable_name="chat_history"),
#             ("human", "{question}"),
#             ("system", "Context information is below. Use this to inform your response, but respond naturally without referencing document numbers:\n{context}"),
#         ])
        
#         return prompt
    
#     def format_context(self, documents: List[str], metadata: List[Dict[str, Any]]) -> str:
#         """Format retrieved documents into context string"""
#         context_parts = []
        
#         for i, (doc, meta) in enumerate(zip(documents, metadata)):
#             source = meta.get('source', 'Unknown source')
#             title = meta.get('title', 'Untitled')
#             similarity = meta.get('similarity', 0.0)
            
#             # Format source for readability but without numbered document references
#             source_name = os.path.basename(source) if isinstance(source, str) else "Unknown"
            
#             # Using tags for internal reference only - the system prompt instructs not to use these in output
#             context_part = f"### CONTENT FROM: {title} ###\n{doc}\nSource: {source_name}\n"
#             context_parts.append(context_part)
        
#         return "\n" + "\n".join(context_parts)
    
#     def format_image_context(self, images: List[Dict[str, Any]]) -> str:
#         """Format image information into context string"""
#         if not images:
#             return ""
        
#         image_parts = []
        
#         for i, img in enumerate(images):
#             title = img.get('title', 'Untitled image')
#             description = img.get('description', 'No description available')
#             tags = img.get('tags', '')
            
#             # Modified to avoid numbered references
#             image_part = f"### IMAGE: {title} ###\nDescription: {description}\nTags: {tags}\n"
#             image_parts.append(image_part)
        
#         return "\n\nRelevant visual information:\n" + "\n".join(image_parts)
    
#     def generate_response(
#         self, 
#         query: str, 
#         documents: List[str], 
#         metadata: List[Dict[str, Any]], 
#         college_name: str,
#         chat_history: List[Dict[str, str]] = None,
#         images: Optional[List[Dict[str, Any]]] = None
#     ) -> str:
#         """Generate a response based on query and retrieved documents"""
#         try:
#             # Format context
#             context = self.format_context(documents, metadata)
            
#             # Add image context if available
#             if images:
#                 context += self.format_image_context(images)
            
#             # Create prompt
#             prompt = self.create_chat_prompt(college_name)
            
#             # Format chat history
#             history = []
#             if chat_history:
#                 for msg in chat_history:
#                     if msg.get('role') == 'user':
#                         history.append(HumanMessage(content=msg.get('content', '')))
#                     elif msg.get('role') == 'assistant':
#                         history.append(SystemMessage(content=msg.get('content', '')))
            
#             # Create chain
#             chain = LLMChain(llm=self.llm, prompt=prompt)
            
#             # Generate response
#             response = chain.run(
#                 question=query,
#                 context=context,
#                 chat_history=history
#             )
            
#             return response
        
#         except Exception as e:
#             logger.error(f"Error generating response: {str(e)}")
#             return "I apologize, but I encountered an error while generating a response. Please try again."


# app/services/llm_service.py
import os
import json
from typing import List, Dict, Any, Optional
import logging
from langchain.schema import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        """Initialize the LLM service with Groq"""
        try:
            self.llm = ChatGroq(
                model=settings.LLM_MODEL,
                api_key=settings.GROQ_API_KEY,
                temperature=0.7,
                top_p=0.9
            )
            logger.info(f"Initialized Groq LLM with model {settings.LLM_MODEL}")
        except Exception as e:
            logger.error(f"Error initializing Groq LLM: {str(e)}")
            raise
    
    def create_chat_prompt(self, college_name: str) -> ChatPromptTemplate:
        """Create a chat prompt template for the college-specific assistant"""
        system_template = f"""You are a helpful assistant for {college_name}. 
Your goal is to provide accurate, helpful, and friendly responses to questions about the college.
When answering questions, use the context provided to you. If the answer cannot be found in the context,
politely state that you don't have that specific information but provide related information if available.

Important: Provide natural responses without referring to document numbers or mentioning which specific document 
information comes from. Simply present the information as if you know it directly. Do not use phrases like 
"According to Document X" or "As mentioned in Document Y." Present information in a conversational, helpful tone
that doesn't reveal the underlying document structure.

For questions about images or visual elements, you can mention relevant images without referencing their numbers,
describing what they show if appropriate.
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_template),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
            ("system", "Context information is below. Use this to inform your response, but respond naturally without referencing document numbers:\n{context}"),
        ])
        
        return prompt
    
    def format_context(self, documents: List[str], metadata: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into context string"""
        context_parts = []
        
        for i, (doc, meta) in enumerate(zip(documents, metadata)):
            source = meta.get('source', 'Unknown source')
            title = meta.get('title', 'Untitled')
            
            # Format source for readability but without numbered document references
            source_name = os.path.basename(source) if isinstance(source, str) else "Unknown"
            
            # Using tags for internal reference only - the system prompt instructs not to use these in output
            context_part = f"### CONTENT FROM: {title} ###\n{doc}\nSource: {source_name}\n"
            context_parts.append(context_part)
        
        return "\n" + "\n".join(context_parts)
    
    def format_image_context(self, images: List[Dict[str, Any]]) -> str:
        """Format image information into context string"""
        if not images:
            return ""
        
        image_parts = []
        
        for i, img in enumerate(images):
            title = img.get('title', 'Untitled image')
            description = img.get('description', 'No description available')
            tags = img.get('tags', '')
            
            # Modified to avoid numbered references
            image_part = f"### IMAGE: {title} ###\nDescription: {description}\nTags: {tags}\n"
            image_parts.append(image_part)
        
        return "\n\nRelevant visual information:\n" + "\n".join(image_parts)
    
    def generate_response(
        self, 
        query: str, 
        documents: List[str], 
        metadata: List[Dict[str, Any]], 
        college_name: str,
        chat_history: List[Dict[str, str]] = None,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generate a response based on query and retrieved documents"""
        try:
            # Format context
            context = self.format_context(documents, metadata)
            
            # Add image context if available
            if images:
                context += self.format_image_context(images)
            
            # Create prompt
            prompt = self.create_chat_prompt(college_name)
            
            # Format chat history
            history = []
            if chat_history:
                for msg in chat_history:
                    if msg.get('role') == 'user':
                        history.append(HumanMessage(content=msg.get('content', '')))
                    elif msg.get('role') == 'assistant':
                        history.append(SystemMessage(content=msg.get('content', '')))
            
            # Create chain
            chain = LLMChain(llm=self.llm, prompt=prompt)
            
            # Generate response
            response = chain.run(
                question=query,
                context=context,
                chat_history=history
            )
            
            return response
        
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I apologize, but I encountered an error while generating a response. Please try again."
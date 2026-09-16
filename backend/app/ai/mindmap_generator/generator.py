import json
from app.services.llm_service import LLMService

async def generate_mindmap_data(text: str) -> dict:
    """
    Generate mind map nodes and edges from text.
    """
    llm = LLMService()
    
    prompt = f"""
    You are an AI assistant that extracts structured knowledge from learning materials to create a mind map.
    Analyze the following text (syllabus, document, or notes) and extract a hierarchical mind map.
    
    The mind map should capture:
    - Main subject/topic (root)
    - Units/modules
    - Chapters
    - Subtopics
    - Important concepts and relationships
    
    Rules for nodes:
    - id: unique string
    - label: short, concise name
    - type: "root", "unit", "chapter", "topic", or "concept"
    - description: short summary or definition (1-2 sentences)
    
    Rules for edges:
    - source: id of the parent node
    - target: id of the child node
    - relationship: string describing how they are connected (e.g. "contains", "is a", "relates to")
    
    Respond STRICTLY with a valid JSON object matching this structure:
    {{
      "title": "Title of the map",
      "nodes": [
        {{ "id": "...", "label": "...", "type": "...", "description": "..." }}
      ],
      "edges": [
        {{ "source": "...", "target": "...", "relationship": "..." }}
      ]
    }}
    
    Do NOT include Markdown formatting outside the JSON object.
    
    Text to analyze:
    {text[:8000]}
    """
    
    response = await llm.generate(prompt=prompt, temperature=0.3)
    
    try:
        # LLMService has an extract_json method we can try to use if needed, 
        # or we just try parsing the text directly since generate() returns raw text.
        cleaned = LLMService._extract_json(response)
        data = json.loads(cleaned)
        return data
    except Exception as e:
        # Fallback empty structure
        return {
            "title": "Generated Mind Map",
            "nodes": [
                { "id": "root", "label": "Document", "type": "root", "description": "Could not parse correctly." }
            ],
            "edges": []
        }

from .rag import rag_search
from .web_search import web_search
from .job_search import job_search

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": (
                "Search the user's own ingested/uploaded documents for relevant "
                "context. Use this when the question is about content the user has "
                "added to Sanctum (notes, PDFs, files they've uploaded)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to run against the user's documents.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the public internet for current or real-time information "
                "that is not part of the user's own documents (news, current "
                "events, facts you don't already know)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to run against the internet.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "job_search",
            "description": (
                "Search for current job listings by keyword/title and optional "
                "location. Use this when the user asks to find jobs, job "
                "openings, or vacancies — not for general web information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Job title or keywords to search for, e.g. 'backend engineer'.",
                    },
                    "location": {
                        "type": "string",
                        "description": "Optional city/region to filter results by, e.g. 'Singapore'.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

TOOL_DISPATCH = {
    "rag_search": rag_search,
    "web_search": web_search,
    "job_search": job_search,
}

from .rag import rag_search
from .web_search import web_search
from .job_search import job_search
from .applications import save_job, draft_cover_letter, list_applications, apply_to_top_matches

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
    {
        "type": "function",
        "function": {
            "name": "save_job",
            "description": (
                "Save a job listing from the most recent job_search results into "
                "the user's tracked applications, by its [N] index number from "
                "that search — do not retype the title/company/url yourself. "
                "Returns the saved application's id."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "The [N] index of the listing from the most recent job_search results.",
                    },
                },
                "required": ["index"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_cover_letter",
            "description": (
                "Draft and save a tailored cover letter for a job that has "
                "already been saved via save_job, using the user's stored "
                "resume profile. Requires the application id returned by "
                "save_job."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {
                        "type": "integer",
                        "description": "The id of the saved application, from save_job's result.",
                    },
                    "job_description": {
                        "type": "string",
                        "description": "Optional fuller job description text to tailor the letter to.",
                    },
                },
                "required": ["application_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_to_top_matches",
            "description": (
                "The preferred tool when the user asks you to 'find and apply "
                "to jobs matching my resume' or similar in one request. Does "
                "everything deterministically in one call: searches for jobs "
                "using the stored profile's skills/location (or an optional "
                "override), saves the top matches, and drafts a tailored "
                "cover letter for each — then returns the exact real results. "
                "Relay this tool's output back to the user close to verbatim; "
                "do not summarize it from memory or invent additional jobs. "
                "This never submits anything — submission is always manual."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "How many top matches to save and draft cover letters for (default 3, max 5).",
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional keyword override. Defaults to the stored profile's skills.",
                    },
                    "location": {
                        "type": "string",
                        "description": "Optional location override. Defaults to the stored profile's location.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_applications",
            "description": (
                "List every job the user has saved or applied to, with its "
                "current status. Use this whenever the user asks what jobs "
                "they've applied to, saved, or what the current status of "
                "their applications is."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

TOOL_DISPATCH = {
    "rag_search": rag_search,
    "web_search": web_search,
    "job_search": job_search,
    "save_job": save_job,
    "draft_cover_letter": draft_cover_letter,
    "apply_to_top_matches": apply_to_top_matches,
    "list_applications": list_applications,
}

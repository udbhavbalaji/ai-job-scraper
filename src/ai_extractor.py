import os
import json
from typing import Union
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY")
)

response_schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "company_name": {"type": "string"},
        "work_arrangement": {"type": "string", "enum": ["on_site", "hybrid", "remote"]},
        "job_type": {"type": "string", "enum": ["full-time", "part-time", "contract", "internship"]},
        "location_city": {"type": "string"},
        "location_country": {"type": "string"},
        "description": {"type": "string"},
        "required_qualifications": {"type": "array", "items": {"type": "string"}},
        "preferred_qualifications": {"type": "array", "items": {"type": "string"}},
        "technical_skills": {"type": "array", "items": {"type": "string"}},
        "non_technical_skills": {"type": "array", "items": {"type": "string"}},
        "salary_min": {"type": "number"},
        "salary_max": {"type": "number"},
        "title": {"type": "string"},
        "salary_currency": {"type": "string", "enum": ["USD", "CAD", "INR", "EUR"]},
        "immigration_requirements": {"type": "string"},
        "benefits": {"type": "array", "items": {"type": "string"}},
        "linguistic_requirements": {"type": "string"},
        "posted_date": {"type": "string"},
    },
}


def get_structured_job_details(
    job_description: str,
) -> dict[str, Union[str, list[str], int]]:
    response = ai_client.chat.completions.create(
        model="x-ai/grok-4-fast:free",
        messages=[
            {
                "role": "system",
                "content": "You are a brilliant text analyzer, who excels at analyzing large pieces of text and extract important information from it into a structured JSON format. Given a job description, retrieve the following information in the following format(JSON): { title: string; company_name: string; work_arrangement: 'on-site' | 'hybrid' | 'remote'; job_type: string; location_city: string; location_country: string; description: string; technical_skills: string[]; non_technical_skills: string[]; salary_min: number; salary_max: number; immigration_reqs: string | undefined; benefits: string[]; linguistic_reqs: string | undefined; posted_date: string; url: string; }",
            },
            {
                "role": "user",
                "content": f"Extract the job posting information from this job: {job_description}",
            },
        ],
        response_format={"type": "json_schema", "json_schema": {"schema": response_schema}}
    )
    json_str_output = json.loads(response.choices[0].message.content)
    return json_str_output

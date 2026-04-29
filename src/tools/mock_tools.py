"""
mock_tools.py
-------------
Fake MongoDB tools — Gemini-compatible parameter types.
No dict/list params — Gemini rejects those in tool schemas.
"""

import json
from agentscope.tool import ToolResponse

MOCK_DATA = [
    {"name": "Aryan Mehta",  "department": "Engineering", "salary": 72000, "city": "Bangalore",   "experience_years": 4, "role": "Backend Developer"},
    {"name": "Priya Sharma", "department": "Engineering", "salary": 85000, "city": "Hyderabad",   "experience_years": 6, "role": "ML Engineer"},
    {"name": "Ronak Das",    "department": "Data",        "salary": 60000, "city": "Bhubaneswar", "experience_years": 2, "role": "Data Analyst"},
    {"name": "Sneha Rao",    "department": "HR",          "salary": 45000, "city": "Pune",        "experience_years": 3, "role": "HR Manager"},
    {"name": "Kiran Patil",  "department": "Engineering", "salary": 95000, "city": "Bangalore",   "experience_years": 8, "role": "Tech Lead"},
    {"name": "Anjali Nair",  "department": "Data",        "salary": 70000, "city": "Chennai",     "experience_years": 5, "role": "Data Scientist"},
    {"name": "Vikram Singh", "department": "HR",          "salary": 48000, "city": "Delhi",       "experience_years": 4, "role": "Recruiter"},
    {"name": "Meera Joshi",  "department": "Engineering", "salary": 67000, "city": "Hyderabad",   "experience_years": 3, "role": "Frontend Developer"},
]


def _make_response(data) -> ToolResponse:
    text = json.dumps(data, indent=2) if not isinstance(data, str) else data
    return ToolResponse(content=[{"type": "text", "text": text}])


def query_collection(
    department: str = "",
    city: str = "",
    role: str = "",
    min_salary: int = 0,
    max_salary: int = 999999,
    min_experience: int = 0,
) -> ToolResponse:
    """
    Query the employees collection with optional filters.
    Leave a parameter empty or 0 to skip that filter.

    Args:
        department: Filter by department name e.g. Engineering, HR, Data
        city: Filter by city name e.g. Bangalore, Hyderabad
        role: Filter by job role e.g. ML Engineer, Data Analyst
        min_salary: Minimum salary (inclusive)
        max_salary: Maximum salary (inclusive)
        min_experience: Minimum years of experience (inclusive)
    """
    results = MOCK_DATA.copy()

    if department:
        results = [r for r in results if r["department"].lower() == department.lower()]
    if city:
        results = [r for r in results if r["city"].lower() == city.lower()]
    if role:
        results = [r for r in results if r["role"].lower() == role.lower()]
    if min_salary > 0:
        results = [r for r in results if r["salary"] >= min_salary]
    if max_salary < 999999:
        results = [r for r in results if r["salary"] <= max_salary]
    if min_experience > 0:
        results = [r for r in results if r["experience_years"] >= min_experience]

    if not results:
        return _make_response("No records found matching the given filters.")
    return _make_response(results)


def aggregate_collection(group_by: str, metric: str = "avg_salary") -> ToolResponse:
    """
    Aggregate employee data by a field.

    Args:
        group_by: Field to group by — one of: department, city, role
        metric: Metric to compute — one of: avg_salary, total_salary, count
    """
    valid_groups = {"department", "city", "role"}
    if group_by not in valid_groups:
        return _make_response(f"Invalid group_by '{group_by}'. Choose from: {valid_groups}")

    groups: dict = {}
    for record in MOCK_DATA:
        key = record.get(group_by, "Unknown")
        groups.setdefault(key, []).append(record)

    result = []
    for key, records in groups.items():
        salaries = [r["salary"] for r in records]
        entry = {group_by: key, "count": len(records)}
        if metric == "avg_salary":
            entry["avg_salary"] = round(sum(salaries) / len(salaries), 2)
        elif metric == "total_salary":
            entry["total_salary"] = sum(salaries)
        elif metric == "count":
            pass  # count already added
        result.append(entry)

    result.sort(key=lambda x: x.get("avg_salary", x.get("total_salary", 0)), reverse=True)
    return _make_response(result)


def get_schema() -> ToolResponse:
    """
    Get available fields and a sample record from the employees collection.
    Call this when unsure about what data is available.
    """
    return _make_response({
        "collection": "employees (MOCK)",
        "fields": list(MOCK_DATA[0].keys()),
        "sample_record": MOCK_DATA[0],
        "departments": list(set(r["department"] for r in MOCK_DATA)),
        "cities": list(set(r["city"] for r in MOCK_DATA)),
        "roles": list(set(r["role"] for r in MOCK_DATA)),
    })
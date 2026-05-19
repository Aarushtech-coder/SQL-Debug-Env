"""Deterministic local solver for smoke tests and no-key demos.

This is not intended to beat the benchmark as an AI agent. It provides a
transparent fallback so the environment, grader, and API can be demonstrated
without requiring a hosted LLM key.
"""

from __future__ import annotations

from typing import Optional


ENGINEERING_FIX = (
    "SELECT name, salary FROM employees "
    "WHERE department = 'Engineering' ORDER BY name"
)


EASY_FIXES = {
    "typo_from": ENGINEERING_FIX,
    "typo_where": ENGINEERING_FIX,
    "typo_select": ENGINEERING_FIX,
    "wrong_column": ENGINEERING_FIX,
    "case_sensitivity": ENGINEERING_FIX,
    "empty_result": ENGINEERING_FIX,
    "null_handling": (
        "SELECT name, salary FROM employees WHERE salary IS NULL ORDER BY name"
    ),
    "agg_missing_group_by": (
        "SELECT department, AVG(salary) AS avg_salary "
        "FROM employees GROUP BY department ORDER BY department"
    ),
    "agg_count_star_vs_column": (
        "SELECT department, COUNT(salary) AS headcount "
        "FROM employees WHERE salary > 80000 "
        "GROUP BY department ORDER BY department"
    ),
    "agg_having_vs_where": (
        "SELECT department, AVG(salary) AS avg_salary "
        "FROM employees GROUP BY department "
        "HAVING AVG(salary) > 88000 ORDER BY department"
    ),
    "no_index_like": ENGINEERING_FIX,
}


MEDIUM_DEFAULT_FIX = """
SELECT
    c.name AS customer_name,
    COUNT(o.id) AS total_orders,
    COALESCE(SUM(oi.amount), 0) AS total_spent
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
LEFT JOIN order_items oi ON o.id = oi.order_id
GROUP BY c.id, c.name
ORDER BY c.name
""".strip()

MEDIUM_FIXES = {
    "inner_join": MEDIUM_DEFAULT_FIX,
    "wrong_join_condition": MEDIUM_DEFAULT_FIX,
    "missing_group_by": MEDIUM_DEFAULT_FIX,
    "wrong_count_column": MEDIUM_DEFAULT_FIX,
    "missing_coalesce": MEDIUM_DEFAULT_FIX,
    "cross_join_missing_on": MEDIUM_DEFAULT_FIX,
    "duplicate_join_inflation": MEDIUM_DEFAULT_FIX,
    "subquery_no_alias": MEDIUM_DEFAULT_FIX,
    "having_wrong_alias": """
SELECT
    c.name AS customer_name,
    COUNT(o.id) AS total_orders,
    COALESCE(SUM(oi.amount), 0) AS total_spent
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
LEFT JOIN order_items oi ON o.id = oi.order_id
GROUP BY c.id, c.name
HAVING COALESCE(SUM(oi.amount), 0) > 50000
ORDER BY c.name
""".strip(),
}


HARD_DEFAULT_FIX = """
SELECT p.name, SUM(s.amount) AS total
FROM products p
JOIN sales s ON p.id = s.product_id
GROUP BY p.id, p.name
HAVING COUNT(s.id) > 5
ORDER BY p.name
""".strip()

HARD_FIXES = {
    "correlated_subquery": HARD_DEFAULT_FIX,
    "missing_having": HARD_DEFAULT_FIX,
    "wrong_join_type": HARD_DEFAULT_FIX,
    "double_count": HARD_DEFAULT_FIX,
    "missing_index_scan": HARD_DEFAULT_FIX,
    "missing_group_by_column": """
SELECT p.name, p.category, SUM(s.amount) AS total
FROM products p
JOIN sales s ON p.id = s.product_id
GROUP BY p.id, p.name, p.category
HAVING COUNT(s.id) > 5
ORDER BY p.name
""".strip(),
    "cte_wrong_filter": """
WITH product_totals AS (
    SELECT p.id, p.name, SUM(s.amount) AS total, COUNT(s.id) AS sale_count
    FROM products p
    JOIN sales s ON p.id = s.product_id
    GROUP BY p.id, p.name
)
SELECT name, total
FROM product_totals
WHERE sale_count > 5
ORDER BY name
""".strip(),
    "cte_self_reference_missing": """
WITH ranked AS (
    SELECT p.name, SUM(s.amount) AS total,
           RANK() OVER (ORDER BY SUM(s.amount) DESC) AS rnk
    FROM products p
    JOIN sales s ON p.id = s.product_id
    GROUP BY p.id, p.name
)
SELECT name, total, rnk
FROM ranked
WHERE rnk <= 10
ORDER BY rnk
""".strip(),
    "subquery_wrong_aggregation_level": """
SELECT p.name,
       SUM(s.amount) AS total,
       (SELECT AVG(amount) FROM sales) AS overall_avg
FROM products p
JOIN sales s ON p.id = s.product_id
GROUP BY p.id, p.name
HAVING SUM(s.amount) > (
    SELECT AVG(total) FROM (
        SELECT SUM(amount) AS total FROM sales GROUP BY product_id
    )
)
ORDER BY p.name
""".strip(),
}


SECURITY_FIXES = {
    "union_injection": ENGINEERING_FIX,
    "wildcard_data_leak": ENGINEERING_FIX,
    "tautology_where_clause": ENGINEERING_FIX,
    "comment_injection": ENGINEERING_FIX,
    "subquery_escalation": (
        "SELECT name, salary FROM employees WHERE salary > "
        "(SELECT MIN(salary) FROM employees WHERE department = 'Engineering') "
        "AND department = 'Engineering' ORDER BY name"
    ),
}


def _lookup_exact(task_id: str, broken_query: str) -> Optional[str]:
    if task_id == "easy":
        from tasks.task_easy import EASY_SCENARIOS

        scenarios = EASY_SCENARIOS
        fixes = EASY_FIXES
    elif task_id == "medium":
        from tasks.task_medium import MEDIUM_SCENARIOS

        scenarios = MEDIUM_SCENARIOS
        fixes = MEDIUM_FIXES
    elif task_id == "hard":
        from tasks.task_hard import HARD_SCENARIOS

        scenarios = HARD_SCENARIOS
        fixes = HARD_FIXES
    elif task_id == "security":
        from tasks.task_security import SECURITY_SCENARIOS

        scenarios = SECURITY_SCENARIOS
        fixes = SECURITY_FIXES
    else:
        return None

    normalized_broken = " ".join(broken_query.split())
    for scenario in scenarios:
        if " ".join(scenario["broken"].split()) == normalized_broken:
            return fixes.get(scenario["name"])
    return None


def solve_observation(obs: dict) -> str:
    """Return a best-effort SQL fix for a reset observation."""
    task_id = obs.get("task_id", "")
    broken_query = obs.get("broken_query", "")
    exact = _lookup_exact(task_id, broken_query)
    if exact:
        return exact

    if task_id == "easy":
        if "salary = NULL" in broken_query:
            return EASY_FIXES["null_handling"]
        if "AVG(salary)" in broken_query and "WHERE AVG" in broken_query:
            return EASY_FIXES["agg_having_vs_where"]
        if "AVG(salary)" in broken_query:
            return EASY_FIXES["agg_missing_group_by"]
        if "COUNT(*)" in broken_query:
            return EASY_FIXES["agg_count_star_vs_column"]
        return ENGINEERING_FIX

    if task_id == "medium":
        if "HAVING total_spent" in broken_query:
            return MEDIUM_FIXES["having_wrong_alias"]
        return MEDIUM_DEFAULT_FIX

    if task_id == "hard":
        if "p.category" in broken_query:
            return HARD_FIXES["missing_group_by_column"]
        if "product_totals" in broken_query:
            return HARD_FIXES["cte_wrong_filter"]
        if "ranked" in broken_query or "rnk" in broken_query:
            return HARD_FIXES["cte_self_reference_missing"]
        if "overall_avg" in broken_query:
            return HARD_FIXES["subquery_wrong_aggregation_level"]
        return HARD_DEFAULT_FIX

    if task_id == "security":
        if "MIN(salary)" in broken_query:
            return SECURITY_FIXES["subquery_escalation"]
        return ENGINEERING_FIX

    # Conservative fallback for generated/demo tasks: fix common syntax typos.
    sql = broken_query
    replacements = {
        "SELCT ": "SELECT ",
        " FORM ": " FROM ",
        " WERE ": " WHERE ",
        " RETRIEVE_FROM ": " FROM ",
        " ORDERD BY ": " ORDER BY ",
    }
    for old, new in replacements.items():
        sql = sql.replace(old, new)
    return sql

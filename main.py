# recipe_suggester.py
"""
Recipe Suggester using CrewAI
- Provide ingredients via CLI string or a plain text file (one ingredient per line or comma-separated).
- Outputs structured JSON with recipe options prioritized by ingredient match.
Note: Set your Crew/LLM API key in the environment variable CREWAI_API_KEY.
"""

import os
import json
from typing import List
from crewai import Agent, Task, Crew, LLM
# put this near the top of your main.py
import json
import re
from typing import Any

def extract_json_from_crew_output(obj: Any):
    """
    Convert various CrewAI/LLM outputs into Python types (list/dict) if possible.
    Returns a Python object ready for json.dumps(...).
    """
    # 1) if already serializable (dict/list), return directly
    if isinstance(obj, (dict, list)):
        return obj

    # 2) If it's a plain string, try to parse JSON; otherwise try to extract JSON substring
    if isinstance(obj, str):
        s = obj.strip()
        # try direct parse
        try:
            return json.loads(s)
        except Exception:
            # find the first JSON array or object in the text
            m = re.search(r'(\[.\]|\{.\})', s, re.S)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    pass
            # no parseable JSON found
            return {"raw_text": s}

    # 3) Some SDK objects expose serialization helpers
    # try common names (to_json, to_dict, dict, data, content, text)
    try_methods = [
        ("to_json", lambda o: json.loads(o.to_json())),
        ("to_dict", lambda o: o.to_dict()),
        ("dict", lambda o: o.dict() if hasattr(o, "dict") else None),
        ("data", lambda o: o.data if hasattr(o, "data") else None),
        ("content", lambda o: o.content if hasattr(o, "content") else None),
        ("text", lambda o: o.text if hasattr(o, "text") else None),
    ]

    for name, fn in try_methods:
        try:
            val = fn(obj)
            if val is None:
                continue
            # if returned a string, attempt JSON parse; otherwise return as-is (dict/list)
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except Exception:
                    # try extracting json substring from this string
                    m = re.search(r'(\[.\]|\{.\})', val, re.S)
                    if m:
                        try:
                            return json.loads(m.group(1))
                        except Exception:
                            continue
                    return {"raw_text_from_{}".format(name): val}
            if isinstance(val, (dict, list)):
                return val
            # if it's some other object, continue to next method
        except Exception:
            continue

    # 4) If we reach here, return a debug-friendly structure
    try:
        return {"raw_repr": repr(obj), "type": type(obj)._name_}
    except Exception:
        return {"raw_str": str(obj), "type": str(type(obj))}

# === LLM Configuration ===
llm = LLM(
    provider="google",                    # or your provider
    model="gemini/gemini-2.0-flash",      # choose appropriate model
    api_key="your_api_key"
 # set CREWAI_API_KEY in your environment
)

# === Agent Setup ===
recipe_agent = Agent(
    role="Recipe Suggester",
    goal=(
        "Given a list of available ingredients, propose and describe recipe options "
        "that maximize use of those ingredients. Provide structured JSON output. "
        "If a recipe requires a small number of common pantry staples (salt, oil, "
        "pepper, water), list them separately and mark whether they are mandatory or optional."
    ),
    backstory="A professional chef who prioritizes ingredient-led, practical recipes.",
    llm=llm,
    verbose=False
)

# === Helpers ===
def parse_ingredients_from_text(text: str) -> List[str]:
    # Accept newline- or comma-separated ingredient lists; normalize to lowercase and strip whitespace
    if not text:
        return []
    # Replace common separators with commas then split
    for ch in ['\n', ';', '|']:
        text = text.replace(ch, ',')
    items = [i.strip().lower() for i in text.split(',') if i.strip()]
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for it in items:
        if it not in seen:
            seen.add(it)
            deduped.append(it)
    return deduped
def load_ingredients_from_file(path: str) -> List[str]:
    """Load ingredients from text or JSON file"""
    with open(path, 'r', encoding='utf-8') as f:
        if path.lower().endswith('.json'):
            # Handle JSON file
            data = json.load(f)
            # Support different JSON structures
            if isinstance(data, list):
                # Direct list of ingredients
                ingredients = data
            elif isinstance(data, dict):
                # Look for common keys that might contain ingredients
                ingredients = (data.get('ingredients') or 
                             data.get('items') or 
                             data.get('list') or 
                             list(data.values())[0] if data else [])
            else:
                raise ValueError("JSON must contain a list or object with ingredients")
            
            # Convert to strings and normalize
            return [str(item).strip().lower() for item in ingredients if item]
        else:
            # Handle text file (existing functionality)
            content = f.read()
            return parse_ingredients_from_text(content)

# === Task and Crew Invocation ===
def suggest_recipes(ingredients: List[str], num_recipes: int = 3, servings: int = 2):
    if not ingredients:
        raise ValueError("No ingredients provided.")

    # Build a tightly constrained prompt: require JSON output and explain schema.
    ingredient_text = ", ".join(ingredients)
    task_description = f"""
    You are given the following list of available ingredients (exact terms; do not invent synonyms unless extremely obvious):
    {ingredient_text}

    Requirements:
        1) Propose exactly {num_recipes} recipe options, ordered by how well they use the provided ingredients.
        2) For each recipe produce a JSON object with fields:
        - title (string)
        - used_ingredients (list)             # ingredients from the provided list that will be used
        - missing_ingredients (list)          # required items not in provided list
        - pantry_staples (list)               # e.g. salt, pepper, oil (each with 'mandatory' or 'optional')
        - servings (int)
        - prep_time_minutes (int)
        - cook_time_minutes (int)
        - difficulty (\"easy\"|\"medium\"|\"hard\")
        - steps (ordered list of step strings) # clear, actionable instructions
        - notes (string)                      # dietary/allergen warnings or substitutions
        3) Do NOT include external links or invent brand names.
        4) If a recipe requires >4 missing ingredients, do not propose it.
        5) Use only common cooking techniques. Prefer recipes that use most of the provided ingredients.
        6) Respond with a single JSON array containing the recipe objects and no additional prose.

        Example schema:
        [
        {{
            "title": "...",
            "used_ingredients": ["..."],
            "missing_ingredients": ["..."],
            "pantry_staples": [{{"name":"salt", "required":"optional"}}],
            "servings": 2,
            "prep_time_minutes": 10,
            "cook_time_minutes": 20,
            "difficulty": "easy",
            "steps": ["...","..."],
            "notes": "..."
        }},
        ...
    ]

    TEXT: Ingredients: {ingredient_text}
    """

    recipe_task = Task(
        name="Suggest Recipes",
        description=task_description,
        agent=recipe_agent,
        expected_output="A JSON array of recipe objects following the schema above.",
        context=[]
    )

    crew = Crew(
        agents=[recipe_agent],
        tasks=[recipe_task],
        verbose=True
    )

    result = crew.kickoff()
    # result is agent/crew output as returned by CrewAI SDK. Try to parse JSON if possible.
    try:
        # attempt to extract JSON from the result (string)
        if isinstance(result, str):
            parsed = json.loads(result)
            return parsed
        else:
            return result
    except Exception:
        # If the LLM returned text plus JSON, attempt to locate JSON substring
        import re
        text = str(result)
        json_match = re.search(r'(\[.*\])', text, re.S)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except Exception:
                pass
        # Fallback: return raw result for inspection
        return {"raw": result}7
# === CLI Entrypoint ===
# === CLI Entrypoint ===
if __name__ == "__main__":
    import argparse
    import re

    parser = argparse.ArgumentParser(description="Recipe Suggester using CrewAI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ingredients", "-i", type=str,
                       help="Comma- or newline-separated ingredient list (quoted).")
    group.add_argument("--file", "-f", type=str,
                       help="Path to a text or JSON file containing ingredients.")
    parser.add_argument("--recipes", "-n", type=int, default=3, help="Number of recipe options to request.")
    parser.add_argument("--servings", "-s", type=int, default=2, help="Default servings for suggested recipes.")
    args = parser.parse_args()

    if args.file:
        ingredients = load_ingredients_from_file(args.file)
    else:
        ingredients = parse_ingredients_from_text(args.ingredients)

    print(f"DEBUG: Parsed ingredients: {ingredients}")

    # Get the raw CrewAI result
    suggestions = suggest_recipes(ingredients, num_recipes=args.recipes, servings=args.servings)

    # Normalize output to a Python object (dict/list) if possible
    def normalize_output(obj):
        if isinstance(obj, (dict, list)):
            return obj
        if isinstance(obj, str):
            try:
                return json.loads(obj)
            except Exception:
                m = re.search(r'(\[.*\]|\{.*\})', obj, re.S)
                if m:
                    return json.loads(m.group(1))
                return {"raw_text": obj}
        if hasattr(obj, "raw"):
            return normalize_output(obj.raw)
        return {"raw_repr": repr(obj)}

    normalized = normalize_output(suggestions)

    # Always overwrite outputs.json
    output_path = "outputs.json"
    with open(output_path, "w", encoding="utf-8") as out_f:
        json.dump(normalized, out_f, ensure_ascii=False, indent=2)

    print(f"✅ Output written to {output_path}")


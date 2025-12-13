BASE64_STORE = {}
url_time = {}
# Global counter for number of questions moved/passed to the next URL
questions_solved = 0
# Total number of questions encountered (increment on every move to next URL)
total_questions = 0
# Per-run/current question folder (set when a run starts)
current_q_folder = None
# Counter for unnamed/unknown questions
unknown_counter = 0
# Next sequential question id (starts at 1)
next_question_id = 1


def next_question_folder() -> str:
    """Return the next `LLMFiles/question_N` folder and increment the counter."""
    global next_question_id
    import os

    name = f"question_{next_question_id}"
    next_question_id += 1
    return os.path.join("LLMFiles", name)


# Track URLs for which a forced-wrong submission has already been performed
forced_fail_submitted = set()


def folder_for_url(url: str) -> str:
    """Return a filesystem-safe folder path under LLMFiles derived from the URL.

    The folder name is produced by URL-encoding the URL. It intentionally uses
    only the URL as requested by the user. The returned path is not created
    by this function; callers should `os.makedirs(path, exist_ok=True)`.
    """
    import os
    from urllib.parse import quote_plus

    if not url:
        # Use a sequential question_N name for unnamed URLs
        global unknown_counter
        unknown_counter += 1
        name = f"question_{unknown_counter}"
        return os.path.join("LLMFiles", name)

    safe = quote_plus(url, safe="")
    # Truncate to avoid filesystem limits
    if len(safe) > 200:
        safe = safe[:200]
    return os.path.join("LLMFiles", safe)

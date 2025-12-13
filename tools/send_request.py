from langchain_core.tools import tool
from shared_store import BASE64_STORE, url_time
import shared_store
import time
import os
import requests
import json
from collections import defaultdict
from typing import Any, Dict, Optional

cache = defaultdict(int)
retry_limit = 4


@tool
def post_request(
    url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None
) -> Any:
    """
    Send an HTTP POST request to the given URL with the provided payload.

    This function is designed for LangGraph applications, where it can be wrapped
    as a Tool or used inside a Runnable to call external APIs, webhooks, or backend
    services during graph execution.
    REMEMBER: This a blocking function so it may take a while to return. Wait for the response.
    Args:
        url (str): The endpoint to send the POST request to.
        payload (Dict[str, Any]): The JSON-serializable request body.
        headers (Optional[Dict[str, str]]): Optional HTTP headers to include
            in the request. If omitted, a default JSON header is applied.

    Returns:
        Any: The response body. If the server returns JSON, a parsed dict is
        returned. Otherwise, the raw text response is returned.

    Raises:
        requests.HTTPError: If the server responds with an unsuccessful status.
        requests.RequestException: For network-related errors.
    """
    # Handling if the answer is a BASE64
    ans = payload.get("answer")

    if isinstance(ans, str) and ans.startswith("BASE64_KEY:"):
        key = ans.split(":", 1)[1]
        payload["answer"] = BASE64_STORE[key]
    headers = headers or {"Content-Type": "application/json"}
    try:
        cur_url = os.getenv("url")
        cache[cur_url] += 1
        sending = payload
        if isinstance(payload.get("answer"), str):
            sending = {
                "answer": payload.get("answer", "")[:100],
                "email": payload.get("email", ""),
                "url": payload.get("url", ""),
            }
        print(f"\nSending Answer \n{json.dumps(sending, indent=4)}\n to url: {url}")
        response = requests.post(url, json=payload, headers=headers)

        # Raise on 4xx/5xx
        response.raise_for_status()

        # Try to return JSON, fallback to raw text
        data = response.json()
        print("Got the response: \n", json.dumps(data, indent=4), "\n")

        # Log server-provided reason (when present) to help debugging
        reason = (data.get("reason") or "").strip()
        if reason:
            print(f"Server reason: {reason}")

        delay = time.time() - url_time.get(cur_url, time.time())
        print(delay)

        # Read correctness before treating missing next-url as termination.
        correct = data.get("correct")
        next_url = data.get("url")

        # If server didn't return a next URL but marked the answer correct,
        # treat this as completion. If the answer was incorrect and next_url
        # is missing, continue into the retry logic instead of terminating.
        if not next_url and correct:
            return "Tasks completed"

        if next_url and next_url not in url_time:
            url_time[next_url] = time.time()
        if not correct:
            cur_time = time.time()
            prev = url_time.get(next_url, time.time())
            if (
                cache[cur_url] >= retry_limit
                or delay >= 180
                or (prev != "0" and (cur_time - float(prev)) > 90)
            ):  # Shouldn't retry
                print("Not retrying, moving on to the next question")
                data = {"url": data.get("url", "")}
            else:  # Retry
                os.environ["offset"] = str(url_time.get(next_url, time.time()))
                print("Retrying..")
                data["url"] = cur_url
                # Include the server reason in the retry message so the LLM
                # can adjust its output to fix the reported issue.
                reason_snippet = reason.replace("\n", " ") if reason else ""
                if reason_snippet:
                    data["message"] = (
                        f"Previous attempt failed: {reason_snippet}. Please adjust your answer and retry."
                    )
                else:
                    data["message"] = "Retry Again!"
        print("Formatted: \n", json.dumps(data, indent=4), "\n")
        forward_url = data.get("url", "")
        # If we're moving to a different URL, update counters:
        # - `total_questions` increments for every new question encountered
        # - `questions_solved` increments only when `correct` is truthy
        if forward_url and forward_url != cur_url:
            try:
                shared_store.total_questions += 1
                if correct:
                    shared_store.questions_solved += 1
            except Exception:
                pass

            # Create and set per-question folder for the new URL so tools
            # write/read files in that folder for this question.
            try:
                # Use sequential question folder for each new question
                folder = shared_store.next_question_folder()
                shared_store.current_q_folder = folder
                os.makedirs(folder, exist_ok=True)
                # write meta for traceability
                try:
                    meta = {"url": forward_url, "created_at": time.time()}
                    with open(os.path.join(folder, "meta.json"), "w") as mf:
                        json.dump(meta, mf)
                except Exception:
                    pass
                print(f"Created per-question folder: {folder}")
            except Exception as e:
                print("Warning: failed to create per-question folder:", e)

            print(
                f"Moved to next url: {forward_url} — total questions solved: {shared_store.questions_solved}/{shared_store.total_questions}"
            )

        os.environ["url"] = forward_url
        if forward_url == next_url:
            os.environ["offset"] = "0"

        return data
    except requests.HTTPError as e:
        # Extract server’s error response
        err_resp = e.response

        try:
            err_data = err_resp.json()
        except ValueError:
            err_data = err_resp.text

        print("HTTP Error Response:\n", err_data)
        return err_data

    except Exception as e:
        print("Unexpected error:", e)
        return str(e)

import os
import sqlite3
import time
import json
import toml
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import transformers
import sys
from tqdm import tqdm

# -------------------- Configuration Loading --------------------
# CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../config.toml")    # TODO: Set your own config path
CONFIG_PATH = "/root/projects/artefact_temp/sol/build/config.toml"

def load_config():
    """Load configuration file and return configuration dictionary"""
    with open(CONFIG_PATH, 'r') as f:
        return toml.load(f)

config = load_config()
llm_api_platform = "https://www.chatgtp.cn/v1/"    # TODO: Set your own LLM API platform, don't add '/chat/completions' at the end
db_path = config['database']['path'] + "/sqlite_Sol.db" # TODO: Set your own database path
llm_model_deepseek_r1 = config['llm']['llm_model_deepseek_r1']
protocol_name = config['project']['protocol_name']
protocol_version = config['project']['protocol_version']
llm_violation_repeat_times = config['llm']['llm_violation_repeat_times']
llm_query_max_attempts = config['llm']['llm_query_max_attempts']
code_slice_replace_mode = config['debug']['code_slice_replace_mode']
# -------------------- Database Operations --------------------
def fetch_rule_code_snippets(db_path):
    """
    Read records from rule_code_snippet table in database
    Returns: list of tuples (rule_desc, code_snippet, call_graph)
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT rule_desc, code_snippet, call_graph, llm_response FROM rule_code_snippet")
            all_records = cursor.fetchall()
            # filtered_records = [record for record in all_records if record[0] in mqtt_rules]
            return all_records
    except sqlite3.DatabaseError as e:
        print(f"Database error: {e}")
        return []
    except Exception as e:
        print(f"Unknown error: {e}")
        return []

# -------------------- Prompt Construction and Query --------------------
def clean_think_content(input_string):
    """
    Remove <think> and </think> and all content between them from the string,
    and remove leading/trailing whitespace from the result string.

    :param input_string: Input string
    :return: Cleaned string
    """
    # Use regular expression to match <think>...</think> and its content
    cleaned_string = re.sub(r'<think>.*?</think>', '', input_string, flags=re.DOTALL)
    # Remove leading and trailing whitespace
    cleaned_string = cleaned_string.strip()
    return cleaned_string

def count_token_length(prompt):
    chat_tokenizer_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "./")
    tokenizer = transformers.AutoTokenizer.from_pretrained(chat_tokenizer_dir, trust_remote_code=True)
    result = tokenizer.encode(prompt)
    return len(result)

def extract_json_from_markdown(input_str):
    # Define Markdown code block markers
    prefix = "```"
    suffix = "```"

    # Check if wrapped by ```
    if (len(input_str) >= len(prefix) + len(suffix) and
        input_str.startswith(prefix) and
        input_str.endswith(suffix)):

        # Extract content between code blocks (remove leading and trailing ```)
        content = input_str[len(prefix):-len(suffix)]

        # Find start and end positions of JSON
        json_start = content.find('{')
        json_end = content.rfind('}')

        # If valid JSON range is found
        if (json_start != -1 and json_end != -1 and json_end > json_start):
            # Extract complete JSON content between {}
            return content[json_start:json_end+1]

        # If no valid JSON is found, return content without ```
        return content

    # If no Markdown markers, directly search for JSON content
    # Handle cases with lots of text but only need to extract {} content
    json_start = input_str.find('{')
    json_end = input_str.rfind('}')

    # If valid JSON range is found, extract JSON part
    if (json_start != -1 and json_end != -1 and json_end > json_start):
        # Extract complete JSON content between {}
        json_content = input_str[json_start:json_end+1]

        # Verify if extracted content is valid JSON
        try:
            import json
            json.loads(json_content)  # Verify JSON format
            return json_content
        except json.JSONDecodeError:
            # If not valid JSON, return original input
            pass

    # If no valid JSON is found or no Markdown markers, return original input
    return input_str

def violation_check_rule_code(protocol_name, protocol_version, rule_desc, code_snippet):
    """Check if code snippet violates rule description"""
    prompt = f"""
Your task is to analyze the provided code slice (#SliceCode) to determine whether it violates the constraints or behaviors specified in the rule description (#Rule) for {protocol_name} {protocol_version}. The code slice represents the developer's implemented code, and the rule description outlines the standards the developer must follow. You need to assess whether the developer adhered to these rules during implementation.

Please follow these steps for the analysis:
1. Understand the specific requirements and constraints in the rule description (#Rule).
2. Examine the key logic and behavior in the code slice (#SliceCode). Note: The numbers in the first column of each line in #SliceCode are line numbers, used to identify the code's position in the file.
3. Determine whether the code slice violates any requirements in the rule description. Note: strictly follow the description in #Rule for checking, do no associate it with any other content. Also note that if the rule describes the message sent by client, check whether #SliceCode contains the corresponding verification logic.
4. If a violation is found, record the detailed reason for the violation, the code lines that violate the rules and their associated filename and function name.
5. If no violation is found, explain how the code correctly adheres to the rule.
6. The response template you must follow is as follows:
If you identify a violation, return the following JSON response:
{{
  "result": "violation found!",
  "reason": "detailed reasons for violations",
  "violations": [
    {{
      "function_name": "function name",
      "filename": "/path/filename",
      "code_lines": [line_number, ...]
    }},
    ...
  ]
}}
If you determine there is no violation, return the following JSON response:
{{
  "result": "no violation found!",
  "reason": "why the code correctly follows to the rule"
}}

#Rule
{rule_desc}

#SliceCode
{code_snippet}
"""
    if count_token_length(prompt) > 98000:
        print("[-] Current first prompt length exceeds 98k, may cause model to reject response, please check prompt")
    def query_with_retries(prompt, thread_id):
        client = OpenAI(api_key=llm_api_key, base_url=llm_api_platform)
        for attempt in range(llm_query_max_attempts):
            try:
                response = client.chat.completions.create(
                    model=llm_model_deepseek_r1,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False
                )
                model_output = clean_think_content(response.choices[0].message.content.strip())
                model_output_clean = extract_json_from_markdown(model_output)
                result = json.loads(model_output_clean)
                print(f"[Thread-{thread_id}] Success on attempt {attempt + 1}")
                return result
            except Exception as e:
                # Ensure model_output_clean variable is available in except block
                if 'model_output_clean' not in locals():
                    model_output_clean = model_output if 'model_output' in locals() else ""

                # Check if it's JSON parsing failure and response contains ```json code block
                if "json" in str(e).lower() or "Expecting value" in str(e):
                    try:
                        # Find content between ```json and ```
                        if "```json" in model_output_clean and "```" in model_output_clean:
                            start_marker = "```json"
                            end_marker = "```"
                            start_idx = model_output_clean.find(start_marker)
                            if start_idx != -1:
                                start_idx += len(start_marker)
                                end_idx = model_output_clean.find(end_marker, start_idx)
                                if end_idx != -1:
                                    json_content = model_output_clean[start_idx:end_idx].strip()
                                    result = json.loads(json_content)
                                    print(f"[Thread-{thread_id}] Success on attempt {attempt + 1} (extracted from markdown)")
                                    return result
                    except Exception:
                        pass  # If extraction and parsing fails, continue with original error handling flow

                print(f"[Thread-{thread_id}] Attempt {attempt + 1} failed: {e}")
                print("failed response: ", model_output_clean)
                time.sleep(2)
        return None

    results = []
    with ThreadPoolExecutor(max_workers=llm_violation_repeat_times) as executor:
        futures = {executor.submit(query_with_retries, prompt, i): i for i in range(llm_violation_repeat_times)}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    analysis_results = get_relevant_function_code(results, code_snippet, rule_desc)
    new_code_snippet = code_snippet
    if analysis_results['success']:
        new_code_snippet = analysis_results['filtered_code']
    second_prompt = generate_self_inconsistency_prompt(protocol_name, protocol_version, rule_desc, new_code_snippet, results)
    if count_token_length(second_prompt) > 98000:
        print("[-] Current second prompt length exceeds 98k, may cause model to reject response, please check prompt")
    second_response = query_with_retries(second_prompt, "second")

    return second_response

def generate_self_inconsistency_prompt(protocol_name, protocol_version, rule_desc, code_snippet, responses):
    """Generate comprehensive analysis prompt"""
    first_response = json.dumps(responses[0]) if len(responses) > 0 else "No response"
    second_response = json.dumps(responses[1]) if len(responses) > 1 else "No response"
    # third_response = json.dumps(responses[2]) if len(responses) > 2 else "No response"

    return f"""
Your previous task was to analyze a given code slice (#SliceCode) to determine whether it violates the constraints or behaviors specified in the rule description (#Rule) for {protocol_name} {protocol_version}. You have received three different analysis responses from a large language model (LLM). Your current task is to synthesize these three analysis results to confirm the final correct answer.

#Instructions:
1. Analyze the Three Responses:
   - Compare the three analysis responses to identify consistency and differences.
   - Highlight any conflicting conclusions or reasoning among the responses.
2. Determine the Correct Answer:
   - If the responses differ, critically evaluate each one by cross-referencing with the code slice and rule description.
   - Base your final answer on the most detailed and logically sound analysis.
3. You must answer in the following manner:
   - If a violation is found, return the following JSON response:
     {{
       "result": "violation found!",
       "reason": "detailed reasons for violations",
       "violations": [
         {{
           "function_name": "function name",
           "filename": "filename",
           "code_lines": [...]
         }},
         ...
       ]
     }}
   - If no violation is found, return the following JSON response:
     {{
       "result": "no violation found!",
       "reason": "why the code correctly follows the rule"
     }}
4. Answer in the format specified in step 3. No irrelevant explanations!

#First Response:
{first_response}

#Second Response:
{second_response}

#Rule
{rule_desc}

#SliceCode
{code_snippet}
"""

def get_relevant_function_code(results: list, code_snippet: str, rule_desc: str):
    """
    Analyze multiple results returned by LLM, extract all function code related to violations from code_snippet
    """
    relevant_functions = set()

    for result in results:
        if result.get("result") == "violation found!":
            for violation in result.get("violations", []):
                if function_name := violation.get("function_name"):
                    relevant_functions.add(function_name)

    if not relevant_functions:
        # print("Note: No function names related to violations were identified")
        return {
            "success": False,
            "relevant_functions": [],
            "filtered_code": ""
        }

    # print(f"Identified relevant functions: {', '.join(relevant_functions)}")

    def filter_code_snippet(code_snippet: str, relevant_functions: set) -> str:
        function_pattern = re.compile(r"^Function:\s+(\w+)", re.MULTILINE)
        filtered_snippet = []
        current_function = None
        keep_function = False

        for line in code_snippet.splitlines():
            match = function_pattern.match(line)
            if match:
                current_function = match.group(1)
                keep_function = current_function in relevant_functions
                if keep_function:
                    filtered_snippet.append(line)
            elif keep_function:
                filtered_snippet.append(line)

        return "\n".join(filtered_snippet)

    filtered_code_snippet = filter_code_snippet(code_snippet, relevant_functions)
    if not filtered_code_snippet.strip():
        raise RuntimeError("No relevant functions found in code snippet, impossible event!", rule_desc)

    return {
        "success": bool(filtered_code_snippet.strip()),
        "relevant_functions": list(relevant_functions),
        "filtered_code": filtered_code_snippet
    }
# -------------------- Database Operations Improvement (Add Retry Mechanism) --------------------
def update_llm_response_in_db(db_path, rule_desc, llm_response):
    """Update function with database lock retry mechanism"""
    max_retries = 1
    retry_delay = 0.5  # Initial retry delay

    for attempt in range(max_retries):
        conn = None
        try:
            conn = sqlite3.connect(db_path, timeout=10)  # Increase connection timeout
            cursor = conn.cursor()

            update_query = """
            UPDATE rule_code_snippet
            SET llm_response = ?
            WHERE rule_desc = ?
            """
            cursor.execute(update_query, (json.dumps(llm_response, ensure_ascii=False), rule_desc))
            conn.commit()

            if cursor.rowcount > 0:
                print(f"Update successful in SQLite")
                return
            else:
                assert False, f"Record for {rule_desc} not found, storage failed"
                return

        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < max_retries - 1:
                print(f"Database lock conflict, retry {attempt+1}...")
                time.sleep(retry_delay * (attempt + 1))
                continue
            else:
                raise
        except Exception as e:
            print(f"Storage failed: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

# -------------------- Main Function --------------------
if __name__ == "__main__":
    global llm_api_key
    llm_api_key = os.getenv("OPENAI_API_KEY")
    if not llm_api_key:
        raise EnvironmentError(
            "Environment variable OPENAI_API_KEY is not set or empty, please set it and retry"
        )

    print(f"Attempting to connect to database: {db_path}")
    data = fetch_rule_code_snippets(db_path)

    if not data:
        print("No data read")
        sys.exit(0)

    print(
        f"Successfully read {len(data)} records, starting concurrent processing..."
    )

    def process_record_wrapper(record):
        idx, (rule_desc, code_snippet, _, llm_response) = record
        print(
            f"\nStarting to process record {idx+1}, rule description: {rule_desc}"
        )

        if llm_response != "" and llm_response != "null" and code_slice_replace_mode == 0:
            print(
                f"Note: Record {idx+1} already has analysis results, skipping processing"
            )
            return

        result = violation_check_rule_code(protocol_name, protocol_version,
                                           rule_desc, code_snippet)

        update_llm_response_in_db(db_path, rule_desc, result)

    MAX_WORKERS = 4
    CHUNK_SIZE = 1

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        tasks = [
            executor.submit(process_record_wrapper, (idx, record))
            for idx, record in enumerate(data)
        ]

        progress_bar = tqdm(total=len(tasks),
                            desc="Processing progress",
                            unit="records")

        for future in as_completed(tasks):
            try:
                future.result()
            except Exception as e:
                progress_bar.write(f"\n\033[31mError: {str(e)}\033[0m")
            finally:
                progress_bar.update(1)
                progress_bar.refresh()

        progress_bar.close()

import os
import json
from datetime import datetime
from typing import List, Optional, Any, Type, Union

from pydantic import BaseModel, ValidationError

import openai

class Promotion(BaseModel):
    product_name: str
    original_price: Optional[float] = None
    discount_value: Optional[float] = None
    discount_type: Optional[str] = None
    final_price: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    conditions: Optional[str] = None
    promotion_code: Optional[str] = None
    raw_text_segment: str

def initialize_llm_client(api_key: str, model_name: str = "gpt-3.5-turbo") -> Any:
    """
    Initializes and configures the client for the LLM API.
    The model_name parameter is included in the signature as per the plan,
    but the openai.OpenAI client itself does not take a model_name at initialization.
    The actual model to be used for API calls will be specified in extract_promotions.
    """
    client = openai.OpenAI(api_key=api_key)
    return client

def _construct_llm_prompt(text_input: str, output_schema: Type[BaseModel]) -> str:
    """
    Constructs the detailed prompt that will be sent to the LLM.
    This prompt includes clear instructions for extraction and the expected JSON output format,
    based on the Pydantic output_schema.
    """
    schema_json = output_schema.schema_json(indent=2)
    prompt = f"""
    You are an expert at extracting promotional information from unstructured text.
    Your task is to identify all promotions described in the provided text and structure them
    into a JSON array of objects. Each object in the array must strictly conform to the following Pydantic schema:

    {schema_json}

    If a field is not explicitly mentioned or inferable, it should be omitted or set to null.
    For dates, use the format YYYY-MM-DDTHH:MM:SS (ISO 8601).
    The 'raw_text_segment' field must contain the exact portion of the original text
    that describes the specific promotion.

    Example of expected output (array of Promotion objects):
    [
      {{
        "product_name": "Product A",
        "original_price": 20.0,
        "discount_value": 5.0,
        "discount_type": "fixed_amount",
        "final_price": 15.0,
        "start_date": "2023-01-01T00:00:00",
        "end_date": "2023-01-31T23:59:59",
        "conditions": "For new customers only",
        "promotion_code": "NEW5OFF",
        "raw_text_segment": "Get 5€ off Product A for new customers with code NEW5OFF, valid until Jan 31st."
      }},
      {{
        "product_name": "Product B",
        "discount_value": 10.0,
        "discount_type": "percentage",
        "final_price": 90.0,
        "start_date": null,
        "end_date": null,
        "conditions": null,
        "promotion_code": null,
        "raw_text_segment": "Product B is 10% off!"
      }}
    ]

    Here is the text to analyze:
    ---
    {text_input}
    ---

    Please provide only the JSON array as your response, with no additional text or explanations.
    """
    return prompt.strip()

def _parse_llm_response(llm_response_content: str, output_schema: Type[BaseModel]) -> List[BaseModel]:
    """
    Parses the raw LLM response (which should be a JSON string) and validates it
    against the defined Pydantic model. Handles JSON parsing and Pydantic validation errors.
    """
    promotions: List[BaseModel] = []
    if not llm_response_content:
        print("Warning: LLM response content was empty.")
        return []

    try:
        # LLM is instructed to return a JSON array of objects.
        parsed_data = json.loads(llm_response_content)

        if not isinstance(parsed_data, list):
            # If LLM returns a single object instead of an array, try to parse it as a single item list
            if isinstance(parsed_data, dict):
                parsed_data = [parsed_data]
            else:
                print(f"Warning: LLM response was not a JSON array or object. Content: {llm_response_content[:200]}...")
                return []

        for item in parsed_data:
            try:
                promotion_obj = output_schema.parse_obj(item)
                promotions.append(promotion_obj)
            except ValidationError as e:
                print(f"Validation error for item: {json.dumps(item)}. Error: {e}")
            except Exception as e:
                print(f"Unexpected error validating item: {json.dumps(item)}. Error: {e}")

    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}. Raw content: {llm_response_content[:200]}...")
    except Exception as e:
        print(f"An unexpected error occurred during parsing: {e}. Raw content: {llm_response_content[:200]}...")

    return promotions

def extract_promotions(text_input: str, llm_client: Any) -> List[Promotion]:
    """
    Orchestrates the complete process of extracting promotions.
    This is the main public function of the module.
    """
    # 1. Construct the LLM prompt
    prompt = _construct_llm_prompt(text_input, Promotion)

    # 2. Send the prompt to the LLM and retrieve the response.
    # The model_name parameter from initialize_llm_client is not directly passed
    # to this function's signature per the plan and QA corrections.
    # A default model name is used for the API call.
    try:
        response = llm_client.chat.completions.create(
            model="gpt-3.5-turbo", # Default model name for the API call
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"} # Request JSON output from the LLM
        )
        llm_response_content = response.choices[0].message.content
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return []

    # 3. Parse and validate the LLM response
    promotions = _parse_llm_response(llm_response_content, Promotion)

    # 4. Return the list of structured Promotion objects
    return promotions
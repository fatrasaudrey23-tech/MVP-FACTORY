import os
import json
from typing import List, Optional, Union

from pydantic import BaseModel, ValidationError, TypeAdapter
from openai import OpenAI, OpenAIError


class PromotionSchema(BaseModel):
    """
    Définit la structure des données que nous attendons d'extraire pour chaque promotion.
    """
    product_or_category: str
    discount_type: str
    discount_value: Union[float, str, None]
    conditions: Optional[List[str]]
    validity_start_date: Optional[str]
    validity_end_date: Optional[str]
    promo_code: Optional[str]
    source_text_snippet: str


def _build_extraction_prompt(raw_text: str, output_schema_json: str) -> str:
    """
    Construit le prompt complet à envoyer au LLM, incluant les instructions,
    le texte à analyser et le format de sortie attendu.
    """
    prompt = f"""
    You are an expert at extracting promotional offers from raw text.
    Your task is to identify all distinct promotional offers in the provided text and
    structure them according to the following JSON schema.

    If no promotions are found, return an empty JSON array: `[]`.
    If multiple promotions are found, return a JSON array of objects, each conforming to the schema.
    Ensure your output is a valid JSON array and contains ONLY the JSON.

    JSON Schema for output:
    {output_schema_json}

    Text to analyze for promotions:
    ---
    {raw_text}
    ---

    Please provide the extracted promotions as a JSON array:
    """
    return prompt


def call_llm_for_extraction(
    prompt: str,
    model_name: str = "gpt-4-turbo-preview",
    temperature: float = 0.0
) -> str:
    """
    Envoie le prompt au Large Language Model et récupère sa réponse brute.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        llm_output = response.choices[0].message.content
        if llm_output is None:
            raise ValueError("LLM returned an empty response content.")
        return llm_output
    except OpenAIError as e:
        print(f"OpenAI API error: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during LLM call: {e}")
        raise


def parse_llm_output(llm_raw_output: str) -> List[PromotionSchema]:
    """
    Prend la sortie brute du LLM, tente de la parser en JSON,
    puis la valide par rapport au `PromotionSchema` à l'aide de Pydantic.
    """
    try:
        # LLM is instructed to return a JSON array of objects.
        # Pydantic TypeAdapter can validate this directly.
        adapter = TypeAdapter(List[PromotionSchema])
        validated_promotions = adapter.validate_json(llm_raw_output)
        return validated_promotions
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON from LLM output: {e}")
        print(f"Raw LLM output: {llm_raw_output}")
        raise ValueError("LLM output is not valid JSON.")
    except ValidationError as e:
        print(f"Pydantic validation failed for LLM output: {e}")
        print(f"Raw LLM output: {llm_raw_output}")
        raise ValueError("LLM output does not conform to PromotionSchema.")
    except Exception as e:
        print(f"An unexpected error occurred during parsing LLM output: {e}")
        raise


def extract_and_structure_promotions(promotion_text: str) -> List[PromotionSchema]:
    """
    Coordonne toutes les étapes pour extraire et structurer les promotions à partir d'un texte donné.
    """
    try:
        # Get the JSON schema for the PromotionSchema model
        # Pydantic V2 uses model_json_schema()
        output_schema_dict = PromotionSchema.model_json_schema()
        output_schema_json = json.dumps(output_schema_dict, indent=2)

        # Build the prompt for the LLM
        prompt = _build_extraction_prompt(promotion_text, output_schema_json)

        # Call the LLM to get raw extraction
        llm_raw_output = call_llm_for_extraction(prompt)

        # Parse and validate the LLM's output
        structured_promotions = parse_llm_output(llm_raw_output)

        return structured_promotions
    except Exception as e:
        print(f"An error occurred during the promotion extraction process: {e}")
        # Depending on requirements, re-raise or return an empty list/specific error object
        raise
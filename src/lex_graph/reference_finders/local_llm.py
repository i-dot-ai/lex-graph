import json
import re
from typing import List

import torch
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from lex_graph.reference_finders.base import ReferenceFinder
from lex_graph.types import FreeTextReference, LLMReference


class LLMReferenceList(BaseModel):
    """List of references."""

    references: List[LLMReference]


class LocalLLMReferenceFinder(ReferenceFinder):
    """Implementation of ReferenceFinder that uses local HuggingFace local models for parsing legislative references."""

    def __init__(
        self,
        model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",  # Phi / Llama / Mistral
        device_map: str = "auto",
        torch_dtype: torch.dtype = torch.float16,
    ):
        """Initialize the reference finder with a local HuggingFace model.

        Args:
            model_name: Name or path of the HuggingFace model to use
            device_map: Device mapping strategy for model loading
            torch_dtype: Data type for model weights
        """
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype=torch_dtype, device_map=device_map
        )

    def _create_prompt(self, text: str) -> str:
        """Create the prompt for the model.

        Args:
            text: The text to analyze

        Returns:
            Formatted prompt string
        """
        system_prompt = (
            """You are a specialized UK and EU legislative free-text reference parser.
Your task is to extract all references to any part of legislation from the text into a structured format.
Only extract explicit references to acts and sections (UK), or directives/regulations and articles (EU).

Rules:
1. Only extract explicit references to provisions of legislation.
2. References to provisions within the same Act should be extracted.
3. Use exact Act names by removing prefixes like "of the", "under the", etc.
4. Only use the exact provision id e.g '5' instead of 'section 5'.
5. Handle both UK and EU legislative formats.
6. You must include at least one field when providing a reference.

Format each reference as JSON:
{
    "act": "name_of_act",
    "section": "section_number", # Also use this for EU legislation articles
}

Text to analyze: """
            + text
        )

        return system_prompt

    def _parse_model_output(self, output: str) -> List[LLMReference]:
        """Parse the model's output into LLMReference objects.

        Args:
            output: Raw model output string

        Returns:
            List of parsed LLMReference objects
        """
        references = []
        try:
            # Find all JSON-like structures in the text
            json_pattern = r"\{[^{}]*\}"
            matches = re.finditer(json_pattern, output)

            for match in matches:
                try:
                    ref_dict = json.loads(match.group())
                    # Create LLMReference object
                    reference = LLMReference(
                        act=ref_dict.get("act"),
                        section=ref_dict.get("section"),
                        article=ref_dict.get("article"),
                    )
                    references.append(reference)
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            print(f"Error parsing model output: {e}")

        return references

    def find_references(self, source_id: str, text: str) -> List[FreeTextReference]:
        """Find all references in the given text using the local model.

        Args:
            source_id: Identifier for the source text
            text: Text to analyze

        Returns:
            List of FreeTextReference objects found in the text
        """
        try:
            # Create prompt and generate response
            prompt = self._create_prompt(text)
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

            outputs = self.model.generate(
                inputs.input_ids,
                max_length=2048,
                temperature=0.0,
                top_p=0.95,
                do_sample=True,
            )

            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response = response[len(prompt) :]  # Remove prompt from response

            # Parse into LLMReference objects
            llm_references = self._parse_model_output(response)

            # Convert to FreeTextReference objects
            references = [
                FreeTextReference(
                    source_id=source_id,
                    act=ref.act,
                    section=ref.section,
                    context=text,
                )
                for ref in llm_references
            ]

            # Sort references consistently
            return sorted(references, key=lambda x: (x.act or "", x.section or ""))

        except Exception as e:
            print(f"Error extracting references: {e}")
            return []

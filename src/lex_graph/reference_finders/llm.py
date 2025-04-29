import json
import os
from typing import List

from openai import AzureOpenAI
from pydantic import BaseModel

from lex_graph.reference_finders.base import ReferenceFinder
from lex_graph.types import FreeTextReference, LLMReference


class LLMReferenceList(BaseModel):
    """List of references."""

    references: List[LLMReference]


class GPTReferenceFinder(ReferenceFinder):
    """Implementation of ReferenceFinder that uses Azure OpenAI for parsing legislative references."""

    def __init__(
        self,
        api_key: str = None,
        endpoint: str = None,
        deployment_name: str = "gpt-4o-mini",
        api_version: str = "2024-10-21",
    ):
        """Initialize the LLM reference finder with Azure OpenAI credentials.

        Args:
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
            deployment_name: Name of the deployed model
            api_version: API version to use (default: 2024-10-21)
        """

        # load from env if not provided
        api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        endpoint = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")

        self.client = AzureOpenAI(
            api_key=api_key, api_version=api_version, azure_endpoint=endpoint
        )
        self.deployment_name = deployment_name

    def _create_prompt(self, text: str) -> List[dict]:
        """Create the prompt for the LLM.

        Args:
            text: The text to analyze

        Returns:
            List of message dictionaries for the chat completion
        """
        system_prompt = """You are a specialized UK and EU legislative free-text reference parser.
Your task is to extract all references to any part of legislation from the text into a structured format.
Only extract explicit references to acts and sections (UK), or directives/regulations and articles (EU).

Rules:
1. Only extract explicit references to provisions of legislation.
2. References to provisions within the same Act should be extracted but the Act should be set to None.
3. If no section is mentioned, set the section to None.
4. Use exact Act names by removing prefixes like "of the", "under the", etc.
5. Only use the exact provision id e.g '5' instead of 'section 5'.
6. Handle both UK and EU legislative formats.
7. You must include at least one field when providing a reference."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

    def find_references(self, source_id: str, text: str) -> List[FreeTextReference]:
        """Find all references in the given text using the LLM.

        Args:
            source_id: Identifier for the source text
            text: Text to analyze

        Returns:
            List of FreeTextReference objects found in the text
        """
        try:
            # Prepare messages for the API call
            messages = self._create_prompt(text)

            # Make the API call
            response = self.client.beta.chat.completions.parse(
                model=self.deployment_name,
                messages=messages,
                temperature=0.0,  # Low temperature for more consistent outputs
                response_format=LLMReferenceList,
            )

            # Parse the response
            result = json.loads(response.choices[0].message.content)

            # Convert to LLMReference objects
            llm_references = [LLMReference(**ref) for ref in result["references"]]

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

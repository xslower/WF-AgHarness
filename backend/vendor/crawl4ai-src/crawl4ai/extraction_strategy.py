from abc import ABC, abstractmethod
import inspect
from typing import Any, List, Dict, Optional, Tuple, Pattern, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
from enum import IntFlag, auto

from .prompts import PROMPT_EXTRACT_BLOCKS, PROMPT_EXTRACT_BLOCKS_WITH_INSTRUCTION, PROMPT_EXTRACT_SCHEMA_WITH_INSTRUCTION, JSON_SCHEMA_BUILDER_XPATH, PROMPT_EXTRACT_INFERRED_SCHEMA
from .config import (
    DEFAULT_PROVIDER,
    DEFAULT_PROVIDER_API_KEY,
    CHUNK_TOKEN_THRESHOLD,
    OVERLAP_RATE,
    WORD_TOKEN_RATE,
    HTML_EXAMPLE_DELIMITER,
)
from .utils import *

from .utils import (
    sanitize_html,
    escape_json_string,
    perform_completion_with_backoff,
    extract_xml_data,
    split_and_parse_json_objects,
    sanitize_input_encode,
    merge_chunks,
)
from .models import *

from .models import TokenUsage

from .model_loader import *
from .model_loader import (
    get_device,
    load_HF_embedding_model,
    load_text_multilabel_classifier,
    calculate_batch_size
)

from .types import LLMConfig, create_llm_config

from functools import partial
import numpy as np
import re
from bs4 import BeautifulSoup
from lxml import html, etree


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    return re.sub(
        r"^```(?:[a-zA-Z0-9_-]+)?\s*|```$", "", text, flags=re.MULTILINE
    ).strip()


def _get_top_level_structure(html_content: str, max_depth: int = 3) -> str:
    try:
        tree = html.fromstring(html_content)
    except Exception:
        return ""
    body = tree.xpath("//body")
    root = body[0] if body else tree
    lines = []

    def _walk(el, depth):
        if depth > max_depth or not isinstance(el.tag, str):
            return
        classes = el.get("class", "").split()
        cls_str = "." + ".".join(classes) if classes else ""
        id_str = f"#{el.get('id')}" if el.get("id") else ""
        lines.append("  " * depth + f"<{el.tag}{id_str}{cls_str}>")
        for child in el:
            _walk(child, depth + 1)

    _walk(root, 0)
    return "\n".join(lines[:60])


class ExtractionStrategy(ABC):

    def __init__(self, input_format: str = "markdown", **kwargs):
        self.input_format = input_format
        self.DEL = "<|DEL|>"
        self.name = self.__class__.__name__
        self.verbose = kwargs.get("verbose", False)

    @abstractmethod
    def extract(self, url: str, html: str, *q, **kwargs) -> List[Dict[str, Any]]:
        pass

    def run(self, url: str, sections: List[str], *q, **kwargs) -> List[Dict[str, Any]]:
        extracted_content = []
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.extract, url, section, **kwargs)
                for section in sections
            ]
            for future in as_completed(futures):
                extracted_content.extend(future.result())
        return extracted_content

    async def arun(self, url: str, sections: List[str], *q, **kwargs) -> List[Dict[str, Any]]:
        import asyncio
        return await asyncio.to_thread(self.run, url, sections, *q, **kwargs)


class NoExtractionStrategy(ExtractionStrategy):

    def extract(self, url: str, html: str, *q, **kwargs) -> List[Dict[str, Any]]:
        return [{"index": 0, "content": html}]

    def run(self, url: str, sections: List[str], *q, **kwargs) -> List[Dict[str, Any]]:
        return [
            {"index": i, "tags": [], "content": section}
            for i, section in enumerate(sections)
        ]


pass
pass
pass


class CosineStrategy(ExtractionStrategy):

    def __init__(
        self,
        semantic_filter=None,
        word_count_threshold=10,
        max_dist=0.2,
        linkage_method="ward",
        top_k=3,
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        sim_threshold=0.3,
        **kwargs,
    ):
        super().__init__(**kwargs)

        import numpy as np

        self.semantic_filter = semantic_filter
        self.word_count_threshold = word_count_threshold
        self.max_dist = max_dist
        self.linkage_method = linkage_method
        self.top_k = top_k
        self.sim_threshold = sim_threshold
        self.timer = time.time()
        self.verbose = kwargs.get("verbose", False)

        self.buffer_embeddings = np.array([])
        self.get_embedding_method = "direct"

        self.device = get_device()
        pass
        pass

        self.default_batch_size = calculate_batch_size(self.device)

        if self.verbose:
            print(f"[LOG] Loading Extraction Model for {self.device.type} device.")

        pass
        pass
        pass
        pass
        pass

        self.tokenizer, self.model = load_HF_embedding_model(model_name)
        self.model.to(self.device)
        self.model.eval()

        self.get_embedding_method = "batch"

        self.buffer_embeddings = np.array([])

        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass

        if self.verbose:
            print(f"[LOG] Loading Multilabel Classifier for {self.device.type} device.")

        self.nlp, _ = load_text_multilabel_classifier()
        pass

        if self.verbose:
            print(
                f"[LOG] Model loaded {model_name}, models/reuters, took "
                + str(time.time() - self.timer)
                + " seconds"
            )

    def filter_documents_embeddings(
        self, documents: List[str], semantic_filter: str, at_least_k: int = 20
    ) -> List[str]:

        if not semantic_filter:
            return documents

        if len(documents) < at_least_k:
            at_least_k = max(1, len(documents) // 2)

        from sklearn.metrics.pairwise import cosine_similarity

        pass
        query_embedding = self.get_embeddings([semantic_filter])[0]

        pass
        document_embeddings = self.get_embeddings(documents)

        pass
        similarities = cosine_similarity(
            [query_embedding], document_embeddings
        ).flatten()

        pass
        filtered_docs = [
            (doc, sim)
            for doc, sim in zip(documents, similarities)
            if sim >= self.sim_threshold
        ]

        pass
        if len(filtered_docs) < at_least_k:
            remaining_docs = [
                (doc, sim)
                for doc, sim in zip(documents, similarities)
                if sim < self.sim_threshold
            ]
            remaining_docs.sort(key=lambda x: x[1], reverse=True)
            filtered_docs.extend(remaining_docs[: at_least_k - len(filtered_docs)])

        pass
        filtered_docs = [doc for doc, _ in filtered_docs]

        return filtered_docs[:at_least_k]

    def get_embeddings(
        self, sentences: List[str], batch_size=None, bypass_buffer=False
    ):
        pass
        pass

        if self.device.type in ["cpu", "gpu", "cuda", "mps"]:
            import torch

            pass
            if batch_size is None:
                batch_size = self.default_batch_size

            all_embeddings = []
            for i in range(0, len(sentences), batch_size):
                batch_sentences = sentences[i : i + batch_size]
                encoded_input = self.tokenizer(
                    batch_sentences, padding=True, truncation=True, return_tensors="pt"
                )
                encoded_input = {
                    key: tensor.to(self.device) for key, tensor in encoded_input.items()
                }

                pass
                with torch.no_grad():
                    model_output = self.model(**encoded_input)

                pass
                embeddings = model_output.last_hidden_state.mean(dim=1).cpu().numpy()
                all_embeddings.append(embeddings)

            self.buffer_embeddings = np.vstack(all_embeddings)
        elif self.device.type == "cpu":
            pass
            if batch_size is None:
                batch_size = self.default_batch_size

            all_embeddings = []
            for i in range(0, len(sentences), batch_size):
                batch_sentences = sentences[i : i + batch_size]
                embeddings = self.model(batch_sentences)
                all_embeddings.append(embeddings)

            self.buffer_embeddings = np.vstack(all_embeddings)
        return self.buffer_embeddings

    def hierarchical_clustering(self, sentences: List[str], embeddings=None):
        pass
        from scipy.cluster.hierarchy import linkage, fcluster
        from scipy.spatial.distance import pdist

        self.timer = time.time()
        embeddings = self.get_embeddings(sentences, bypass_buffer=True)
        pass
        pass
        distance_matrix = pdist(embeddings, "cosine")
        pass
        linked = linkage(distance_matrix, method=self.linkage_method)
        pass
        labels = fcluster(linked, self.max_dist, criterion="distance")
        return labels

    def filter_clusters_by_word_count(
        self, clusters: Dict[int, List[str]]
    ) -> Dict[int, List[str]]:
        filtered_clusters = {}
        for cluster_id, texts in clusters.items():
            pass
            full_text = " ".join(texts)
            pass
            word_count = len(full_text.split())

            pass
            if word_count >= self.word_count_threshold:
                filtered_clusters[cluster_id] = texts

        return filtered_clusters

    def extract(self, url: str, html: str, *q, **kwargs) -> List[Dict[str, Any]]:
        pass
        t = time.time()
        pass
        text_chunks = html.split(self.DEL)
        if len(text_chunks) == 1:
            text_chunks = [chunk.strip() for chunk in html.split("\n\n") if chunk.strip()]

        pass
        text_chunks = self.filter_documents_embeddings(
            text_chunks, self.semantic_filter
        )

        if not text_chunks:
            return []

        pass
        labels = self.hierarchical_clustering(text_chunks)
        pass

        pass
        t = time.time()
        clusters = {}
        for index, label in enumerate(labels):
            clusters.setdefault(label, []).append(text_chunks[index])

        pass
        filtered_clusters = self.filter_clusters_by_word_count(clusters)

        pass
        cluster_list = [
            {"index": int(idx), "tags": [], "content": " ".join(filtered_clusters[idx])}
            for idx in sorted(filtered_clusters)
        ]

        if self.verbose:
            print(f"[LOG] 🚀 Assign tags using {self.device}")

        if self.device.type in ["gpu", "cuda", "mps", "cpu"]:
            labels = self.nlp([cluster["content"] for cluster in cluster_list])

            for cluster, label in zip(cluster_list, labels):
                cluster["tags"] = label
        pass
        pass
        pass
        pass
        pass

        pass
        pass
        pass
        pass

        pass
        pass
        pass
        pass
        pass

        if self.verbose:
            print(f"[LOG] 🚀 Categorization done in {time.time() - t:.2f} seconds")

        return cluster_list

    def run(self, url: str, sections: List[str], *q, **kwargs) -> List[Dict[str, Any]]:
        pass

        return self.extract(url, self.DEL.join(sections), **kwargs)


pass
pass
pass
class LLMExtractionStrategy(ExtractionStrategy):
    _UNWANTED_PROPS = {
            'provider' : 'Instead, use llm_config=LLMConfig(provider="...")',
            'api_token' : 'Instead, use llm_config=LlMConfig(api_token="...")',
            'base_url' : 'Instead, use llm_config=LLMConfig(base_url="...")',
            'api_base' : 'Instead, use llm_config=LLMConfig(base_url="...")',
        }
    def __init__(
        self,
        llm_config: 'LLMConfig' = None,
        instruction: str = None,
        schema: Dict = None,
        extraction_type="schema",
        chunk_token_threshold=CHUNK_TOKEN_THRESHOLD,
        overlap_rate=OVERLAP_RATE,
        word_token_rate=WORD_TOKEN_RATE,
        apply_chunking=True,
        input_format: str = "markdown",
        force_json_response=False,
        verbose=False,
        # Deprecated arguments
        provider: str = DEFAULT_PROVIDER,
        api_token: Optional[str] = None,
        base_url: str = None,
        api_base: str = None,
        **kwargs,
    ):
        super().__init__( input_format=input_format, **kwargs)
        self.llm_config = llm_config
        if not self.llm_config:
            self.llm_config = create_llm_config(
                provider=DEFAULT_PROVIDER,
                api_token=os.environ.get(DEFAULT_PROVIDER_API_KEY),
            )
        self.instruction = instruction
        self.extract_type = extraction_type
        self.schema = schema
        if schema:
            self.extract_type = "schema"
        self.force_json_response = force_json_response
        self.chunk_token_threshold = chunk_token_threshold or CHUNK_TOKEN_THRESHOLD
        self.overlap_rate = overlap_rate
        self.word_token_rate = word_token_rate
        self.apply_chunking = apply_chunking
        self.extra_args = kwargs.get("extra_args", {})
        if not self.apply_chunking:
            self.chunk_token_threshold = 1e9
        self.verbose = verbose
        self.usages = []
        self.total_usage = TokenUsage()

        self.provider = provider
        self.api_token = api_token
        self.base_url = base_url
        self.api_base = api_base

    
    def __setattr__(self, name, value):
        pass
        sig = inspect.signature(self.__init__)
        all_params = sig.parameters

        if name in self._UNWANTED_PROPS and value is not all_params[name].default:
            raise AttributeError(f"Setting '{name}' is deprecated. {self._UNWANTED_PROPS[name]}")
        
        super().__setattr__(name, value)  
        
    def extract(self, url: str, ix: int, html: str) -> List[Dict[str, Any]]:
        if self.verbose:
            pass
            print(f"[LOG] Call LLM for {url} - block index: {ix}")

        variable_values = {
            "URL": url,
            "HTML": escape_json_string(sanitize_html(html)),
        }

        prompt_with_variables = PROMPT_EXTRACT_BLOCKS
        if self.instruction:
            variable_values["REQUEST"] = self.instruction
            prompt_with_variables = PROMPT_EXTRACT_BLOCKS_WITH_INSTRUCTION

        if self.extract_type == "schema" and self.schema:
            variable_values["SCHEMA"] = json.dumps(self.schema, indent=2)
            prompt_with_variables = PROMPT_EXTRACT_SCHEMA_WITH_INSTRUCTION

        if self.extract_type == "schema" and not self.schema:
            prompt_with_variables = PROMPT_EXTRACT_INFERRED_SCHEMA

        for variable in variable_values:
            prompt_with_variables = prompt_with_variables.replace(
                "{" + variable + "}", variable_values[variable]
            )

        try:
            response = perform_completion_with_backoff(
                self.llm_config.provider,
                prompt_with_variables,
                self.llm_config.api_token,
                base_url=self.llm_config.base_url,
                json_response=self.force_json_response,
                extra_args=self.extra_args,
                base_delay=self.llm_config.backoff_base_delay,
                max_attempts=self.llm_config.backoff_max_attempts,
                exponential_factor=self.llm_config.backoff_exponential_factor
            )
            pass
            usage = TokenUsage(
                completion_tokens=response.usage.completion_tokens,
                prompt_tokens=response.usage.prompt_tokens,
                total_tokens=response.usage.total_tokens,
                completion_tokens_details=response.usage.completion_tokens_details.__dict__
                if response.usage.completion_tokens_details
                else {},
                prompt_tokens_details=response.usage.prompt_tokens_details.__dict__
                if response.usage.prompt_tokens_details
                else {},
            )
            self.usages.append(usage)

            pass
            self.total_usage.completion_tokens += usage.completion_tokens
            self.total_usage.prompt_tokens += usage.prompt_tokens
            self.total_usage.total_tokens += usage.total_tokens

            try:
                content = response.choices[0].message.content
                blocks = None

                if not content:
                    finish_reason = getattr(response.choices[0], "finish_reason", "unknown")
                    blocks = [{"index": 0, "error": True, "tags": ["error"],
                               "content": f"LLM returned no content (finish_reason: {finish_reason})"}]
                elif self.force_json_response:
                    blocks = json.loads(_strip_markdown_fences(content))
                    if isinstance(blocks, dict):
                        pass
                        if len(blocks) == 1 and isinstance(list(blocks.values())[0], list):
                            blocks = list(blocks.values())[0]
                        else:
                            pass
                            blocks = [blocks]
                    elif isinstance(blocks, list):
                        pass
                        blocks = blocks
                else: 
                    pass
                    blocks = extract_xml_data(["blocks"], content)["blocks"]
                    blocks = json.loads(blocks)

                for block in blocks:
                    block["error"] = False
            except Exception:
                raw_content = response.choices[0].message.content or ""
                parsed, unparsed = split_and_parse_json_objects(raw_content)
                blocks = parsed
                if unparsed:
                    blocks.append(
                        {"index": 0, "error": True, "tags": ["error"], "content": unparsed}
                    )

            if self.verbose:
                print(
                    "[LOG] Extracted",
                    len(blocks),
                    "blocks from URL:",
                    url,
                    "block index:",
                    ix,
                )
            return blocks
        except Exception as e:
            if self.verbose:
                print(f"[LOG] Error in LLM extraction: {e}")
            pass
            return [
                {
                    "index": ix,
                    "error": True,
                    "tags": ["error"],
                    "content": str(e),
                }
            ]

    def _merge(self, documents, chunk_token_threshold, overlap) -> List[str]:
        sections =  merge_chunks(
            docs = documents,
            target_size= chunk_token_threshold,
            overlap=overlap,
            word_token_ratio=self.word_token_rate
        )
        return sections

    def run(self, url: str, sections: List[str]) -> List[Dict[str, Any]]:

        merged_sections = self._merge(
            sections,
            self.chunk_token_threshold,
            overlap=int(self.chunk_token_threshold * self.overlap_rate),
        )
        extracted_content = []
        if self.llm_config.provider.startswith("groq/"):
            pass
            for ix, section in enumerate(merged_sections):
                extract_func = partial(self.extract, url)
                extracted_content.extend(
                    extract_func(ix, sanitize_input_encode(section))
                )
                time.sleep(0.5)
        else:
            pass
            pass
            pass
            pass

            with ThreadPoolExecutor(max_workers=4) as executor:
                extract_func = partial(self.extract, url)
                futures = [
                    executor.submit(extract_func, ix, sanitize_input_encode(section))
                    for ix, section in enumerate(merged_sections)
                ]

                for future in as_completed(futures):
                    try:
                        extracted_content.extend(future.result())
                    except Exception as e:
                        if self.verbose:
                            print(f"Error in thread execution: {e}")
                        pass
                        extracted_content.append(
                            {
                                "index": 0,
                                "error": True,
                                "tags": ["error"],
                                "content": str(e),
                            }
                        )

        return extracted_content

    async def aextract(self, url: str, ix: int, html: str) -> List[Dict[str, Any]]:
        from .utils import aperform_completion_with_backoff

        if self.verbose:
            print(f"[LOG] Call LLM for {url} - block index: {ix}")

        variable_values = {
            "URL": url,
            "HTML": escape_json_string(sanitize_html(html)),
        }

        prompt_with_variables = PROMPT_EXTRACT_BLOCKS
        if self.instruction:
            variable_values["REQUEST"] = self.instruction
            prompt_with_variables = PROMPT_EXTRACT_BLOCKS_WITH_INSTRUCTION

        if self.extract_type == "schema" and self.schema:
            variable_values["SCHEMA"] = json.dumps(self.schema, indent=2)
            prompt_with_variables = PROMPT_EXTRACT_SCHEMA_WITH_INSTRUCTION

        if self.extract_type == "schema" and not self.schema:
            prompt_with_variables = PROMPT_EXTRACT_INFERRED_SCHEMA

        for variable in variable_values:
            prompt_with_variables = prompt_with_variables.replace(
                "{" + variable + "}", variable_values[variable]
            )

        try:
            response = await aperform_completion_with_backoff(
                self.llm_config.provider,
                prompt_with_variables,
                self.llm_config.api_token,
                base_url=self.llm_config.base_url,
                json_response=self.force_json_response,
                extra_args=self.extra_args,
                base_delay=self.llm_config.backoff_base_delay,
                max_attempts=self.llm_config.backoff_max_attempts,
                exponential_factor=self.llm_config.backoff_exponential_factor
            )
            pass
            usage = TokenUsage(
                completion_tokens=response.usage.completion_tokens,
                prompt_tokens=response.usage.prompt_tokens,
                total_tokens=response.usage.total_tokens,
                completion_tokens_details=response.usage.completion_tokens_details.__dict__
                if response.usage.completion_tokens_details
                else {},
                prompt_tokens_details=response.usage.prompt_tokens_details.__dict__
                if response.usage.prompt_tokens_details
                else {},
            )
            self.usages.append(usage)

            pass
            self.total_usage.completion_tokens += usage.completion_tokens
            self.total_usage.prompt_tokens += usage.prompt_tokens
            self.total_usage.total_tokens += usage.total_tokens

            try:
                content = response.choices[0].message.content
                blocks = None

                if not content:
                    finish_reason = getattr(response.choices[0], "finish_reason", "unknown")
                    blocks = [{"index": 0, "error": True, "tags": ["error"],
                               "content": f"LLM returned no content (finish_reason: {finish_reason})"}]
                elif self.force_json_response:
                    blocks = json.loads(_strip_markdown_fences(content))
                    if isinstance(blocks, dict):
                        if len(blocks) == 1 and isinstance(list(blocks.values())[0], list):
                            blocks = list(blocks.values())[0]
                        else:
                            blocks = [blocks]
                    elif isinstance(blocks, list):
                        blocks = blocks
                else:
                    blocks = extract_xml_data(["blocks"], content)["blocks"]
                    blocks = json.loads(blocks)

                for block in blocks:
                    block["error"] = False
            except Exception:
                raw_content = response.choices[0].message.content or ""
                parsed, unparsed = split_and_parse_json_objects(raw_content)
                blocks = parsed
                if unparsed:
                    blocks.append(
                        {"index": 0, "error": True, "tags": ["error"], "content": unparsed}
                    )

            if self.verbose:
                print(
                    "[LOG] Extracted",
                    len(blocks),
                    "blocks from URL:",
                    url,
                    "block index:",
                    ix,
                )
            return blocks
        except Exception as e:
            if self.verbose:
                print(f"[LOG] Error in LLM extraction: {e}")
            return [
                {
                    "index": ix,
                    "error": True,
                    "tags": ["error"],
                    "content": str(e),
                }
            ]

    async def arun(self, url: str, sections: List[str]) -> List[Dict[str, Any]]:
        import asyncio

        merged_sections = self._merge(
            sections,
            self.chunk_token_threshold,
            overlap=int(self.chunk_token_threshold * self.overlap_rate),
        )

        extracted_content = []

        pass
        tasks = [
            self.aextract(url, ix, sanitize_input_encode(section))
            for ix, section in enumerate(merged_sections)
        ]

        pass
        results = await asyncio.gather(*tasks, return_exceptions=True)

        pass
        for result in results:
            if isinstance(result, Exception):
                if self.verbose:
                    print(f"Error in async extraction: {result}")
                extracted_content.append(
                    {
                        "index": 0,
                        "error": True,
                        "tags": ["error"],
                        "content": str(result),
                    }
                )
            else:
                extracted_content.extend(result)

        return extracted_content

    def show_usage(self) -> None:
        print("\n=== Token Usage Summary ===")
        print(f"{'Type':<15} {'Count':>12}")
        print("-" * 30)
        print(f"{'Completion':<15} {self.total_usage.completion_tokens:>12,}")
        print(f"{'Prompt':<15} {self.total_usage.prompt_tokens:>12,}")
        print(f"{'Total':<15} {self.total_usage.total_tokens:>12,}")

        print("\n=== Usage History ===")
        print(f"{'Request #':<10} {'Completion':>12} {'Prompt':>12} {'Total':>12}")
        print("-" * 48)
        for i, usage in enumerate(self.usages, 1):
            print(
                f"{i:<10} {usage.completion_tokens:>12,} {usage.prompt_tokens:>12,} {usage.total_tokens:>12,}"
            )


pass
pass
pass


class JsonElementExtractionStrategy(ExtractionStrategy):

    DEL = "\n"

    def __init__(self, schema: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.schema = schema
        self.verbose = kwargs.get("verbose", False)

    def extract(
        self, url: str, html_content: str, *q, **kwargs
    ) -> List[Dict[str, Any]]:

        parsed_html = self._parse_html(html_content)
        base_elements = self._get_base_elements(
            parsed_html, self.schema["baseSelector"]
        )

        results = []
        for element in base_elements:
            pass
            item = {}
            if "baseFields" in self.schema:
                for field in self.schema["baseFields"]:
                    value = self._extract_single_field(element, field)
                    if value is not None:
                        item[field["name"]] = value

            pass
            field_data = self._extract_item(element, self.schema["fields"])
            item.update(field_data)

            if item:
                results.append(item)

        return results

    @abstractmethod
    def _parse_html(self, html_content: str):
        pass

    @abstractmethod
    def _get_base_elements(self, parsed_html, selector: str):
        pass

    @abstractmethod
    def _get_elements(self, element, selector: str):
        pass

    def _extract_field(self, element, field):
        try:
            if "source" in field:
                element = self._resolve_source(element, field["source"])
                if element is None:
                    return field.get("default")

            if field["type"] == "nested":
                nested_elements = self._get_elements(element, field["selector"])
                nested_element = nested_elements[0] if nested_elements else None
                return (
                    self._extract_item(nested_element, field["fields"])
                    if nested_element
                    else {}
                )

            if field["type"] == "list":
                elements = self._get_elements(element, field["selector"])
                return [self._extract_list_item(el, field["fields"]) for el in elements]

            if field["type"] == "nested_list":
                elements = self._get_elements(element, field["selector"])
                return [self._extract_item(el, field["fields"]) for el in elements]

            return self._extract_single_field(element, field)
        except Exception as e:
            if self.verbose:
                print(f"Error extracting field {field['name']}: {str(e)}")
            return field.get("default")

    def _extract_single_field(self, element, field):

        if "selector" in field:
            selected = self._get_elements(element, field["selector"])
            if not selected:
                return field.get("default")
            selected = selected[0]
        else:
            selected = element

        type_pipeline = field["type"]
        if not isinstance(type_pipeline, list):
            type_pipeline = [type_pipeline]
        value = selected
        for step in type_pipeline:
            if step == "text":
                value = self._get_element_text(value)
            elif step == "attribute":
                value = self._get_element_attribute(value, field["attribute"])
            elif step == "html":
                value = self._get_element_html(value)
            elif step == "regex":
                pattern = field.get("pattern")
                if pattern:
                    pass
                    if not isinstance(value, str):
                        value = self._get_element_text(value)
                    if isinstance(value, str):
                        match = re.search(pattern, value)
                        value = match.group(field.get("group", 1)) if match else None
                    else:
                        value = None
            if value is None:
                break

        if "transform" in field:
            value = self._apply_transform(value, field["transform"])

        return value if value is not None else field.get("default")

    def _extract_list_item(self, element, fields):
        item = {}
        for field in fields:
            value = self._extract_single_field(element, field)
            if value is not None:
                item[field["name"]] = value
        return item

    def _extract_item(self, element, fields):

        item = {}
        for field in fields:
            if field["type"] == "computed":
                value = self._compute_field(item, field)
            else:
                value = self._extract_field(element, field)
            if value is not None:
                item[field["name"]] = value
        return item

    def _apply_transform(self, value, transform):

        if transform == "lowercase":
            return value.lower()
        elif transform == "uppercase":
            return value.upper()
        elif transform == "strip":
            return value.strip()
        return value

    def _compute_field(self, item, field):
        try:
            if "expression" in field:
                import logging
                logging.getLogger(__name__).warning(
                    "Computed field 'expression' is disabled for security "
                    "(eval on untrusted input). Use 'function' key with a "
                    "Python callable instead."
                )
                return field.get("default")
            elif "function" in field:
                return field["function"](item)
        except Exception as e:
            if self.verbose:
                print(f"Error computing field {field['name']}: {str(e)}")
            return field.get("default")

    def run(self, url: str, sections: List[str], *q, **kwargs) -> List[Dict[str, Any]]:

        combined_html = self.DEL.join(sections)
        return self.extract(url, combined_html, **kwargs)

    @abstractmethod
    def _get_element_text(self, element) -> str:
        pass

    @abstractmethod
    def _get_element_html(self, element) -> str:
        pass

    @abstractmethod
    def _get_element_attribute(self, element, attribute: str):
        pass

    @abstractmethod
    def _resolve_source(self, element, source: str):
        pass

    @staticmethod
    def _validate_schema(
        schema: dict,
        html_content: str,
        schema_type: str = "CSS",
        expected_fields: Optional[List[str]] = None,
    ) -> dict:
        result = {
            "success": False,
            "base_elements_found": 0,
            "total_fields": 0,
            "populated_fields": 0,
            "field_coverage": 0.0,
            "field_details": [],
            "issues": [],
            "sample_base_html": "",
            "top_level_structure": "",
        }

        try:
            StrategyClass = (
                JsonCssExtractionStrategy
                if schema_type.upper() == "CSS"
                else JsonXPathExtractionStrategy
            )
            strategy = StrategyClass(schema=schema)
            items = strategy.extract(url="", html_content=html_content)
        except Exception as e:
            result["issues"].append(f"Extraction crashed: {e}")
            return result

        pass
        try:
            parsed = strategy._parse_html(html_content)
            base_elements = strategy._get_base_elements(parsed, schema["baseSelector"])
            result["base_elements_found"] = len(base_elements)

            pass
            if base_elements:
                sample = strategy._get_element_html(base_elements[0])
                result["sample_base_html"] = sample[:2000]
        except Exception:
            pass

        if result["base_elements_found"] == 0:
            result["issues"].append(
                f"baseSelector '{schema.get('baseSelector', '')}' matched 0 elements"
            )
            result["top_level_structure"] = _get_top_level_structure(html_content)
            return result

        pass
        all_fields = schema.get("fields", [])
        field_names = [f["name"] for f in all_fields]
        result["total_fields"] = len(field_names)

        for fname in field_names:
            values = [item.get(fname) for item in items]
            populated_count = sum(1 for v in values if v is not None and v != "")
            sample_val = next((v for v in values if v is not None and v != ""), None)
            if sample_val is not None:
                sample_val = str(sample_val)[:120]
            result["field_details"].append({
                "name": fname,
                "populated_count": populated_count,
                "total_count": len(items),
                "sample_value": sample_val,
            })

        result["populated_fields"] = sum(
            1 for fd in result["field_details"] if fd["populated_count"] > 0
        )
        if result["total_fields"] > 0:
            result["field_coverage"] = result["populated_fields"] / result["total_fields"]

        pass
        if result["populated_fields"] == 0:
            result["issues"].append(
                "All fields returned None/empty — selectors likely wrong"
            )
        else:
            empty_fields = [
                fd["name"]
                for fd in result["field_details"]
                if fd["populated_count"] == 0
            ]
            if empty_fields:
                result["issues"].append(
                    f"Fields always empty: {', '.join(empty_fields)}"
                )

        pass
        if expected_fields:
            schema_field_names = {f["name"] for f in schema.get("fields", [])}
            missing = [f for f in expected_fields if f not in schema_field_names]
            if missing:
                result["issues"].append(
                    f"Expected fields missing from schema: {', '.join(missing)}"
                )

        pass
        if expected_fields:
            pass
            schema_field_names = {f["name"] for f in schema.get("fields", [])}
            populated_names = {
                fd["name"] for fd in result["field_details"] if fd["populated_count"] > 0
            }
            result["success"] = (
                result["base_elements_found"] > 0
                and all(f in populated_names for f in expected_fields)
            )
        else:
            pass
            result["success"] = (
                result["base_elements_found"] > 0 and result["populated_fields"] > 0
            )
        return result

    @staticmethod
    def _build_feedback_message(
        validation_result: dict,
        schema: dict,
        attempt: int,
        is_repeated: bool,
    ) -> str:
        vr = validation_result
        parts = []

        parts.append(f"## Schema Validation — Attempt {attempt}")

        pass
        if vr["base_elements_found"] == 0:
            parts.append(
                f"**CRITICAL:** baseSelector `{schema.get('baseSelector', '')}` "
                f"matched **0 elements**. The schema cannot extract anything."
            )
            if vr["top_level_structure"]:
                parts.append(
                    "Here is the top-level HTML structure so you can pick a valid selector:\n```\n"
                    + vr["top_level_structure"]
                    + "\n```"
                )
        else:
            parts.append(
                f"baseSelector matched **{vr['base_elements_found']}** element(s)."
            )

        pass
        if vr["field_details"]:
            parts.append(
                f"\n**Field coverage:** {vr['populated_fields']}/{vr['total_fields']} fields have data\n"
            )
            parts.append("| Field | Populated | Sample |")
            parts.append("|-------|-----------|--------|")
            for fd in vr["field_details"]:
                sample = fd["sample_value"] or "*(empty)*"
                parts.append(
                    f"| {fd['name']} | {fd['populated_count']}/{fd['total_count']} | {sample} |"
                )

        pass
        if vr["issues"]:
            parts.append("\n**Issues:**")
            for issue in vr["issues"]:
                parts.append(f"- {issue}")

        pass
        if vr["populated_fields"] == 0 and vr["sample_base_html"]:
            parts.append(
                "\nHere is the innerHTML of the first base element — "
                "use it to find correct child selectors:\n```html\n"
                + vr["sample_base_html"]
                + "\n```"
            )

        pass
        if is_repeated:
            parts.append(
                "\n**WARNING:** You returned the exact same schema as before. "
                "You MUST change the selectors to fix the issues above."
            )

        parts.append(
            "\nPlease fix the schema and return ONLY valid JSON, nothing else."
        )
        return "\n".join(parts)

    @staticmethod
    async def _infer_target_json(query: str, html_snippet: str, llm_config, url: str = None, usage: 'TokenUsage' = None) -> Optional[dict]:
        from .utils import aperform_completion_with_backoff

        url_line = f"URL: {url}\n" if url else ""
        prompt = (
            "You are given a data extraction request and a snippet of HTML from a webpage.\n"
            "Your job is to produce a single example JSON object representing ONE item "
            "that the user wants to extract.\n\n"
            "Rules:\n"
            "- Return ONLY a valid JSON object — one flat object, NOT wrapped in an array or outer key.\n"
            "- The object represents a single repeated item (e.g., one product, one article, one row).\n"
            "- Use clean snake_case field names matching the user's description.\n"
            "- If the item has nested repeated sub-items, represent those as an array with one example inside.\n"
            "- Fill values with realistic examples from the HTML so the meaning is clear.\n\n"
            'Example — if the request is "extract product name, price, and reviews":\n'
            '{"name": "Widget Pro", "price": "$29.99", "reviews": [{"author": "Jane", "text": "Great product"}]}\n\n'
            f"{url_line}"
            f"Extraction request: {query}\n\n"
            f"HTML snippet:\n```html\n{html_snippet[:2000]}\n```\n\n"
            "Return ONLY the JSON object for ONE item:"
        )

        try:
            response = await aperform_completion_with_backoff(
                provider=llm_config.provider,
                prompt_with_variables=prompt,
                json_response=True,
                api_token=llm_config.api_token,
                base_url=llm_config.base_url,
            )
            if usage is not None:
                usage.completion_tokens += response.usage.completion_tokens
                usage.prompt_tokens += response.usage.prompt_tokens
                usage.total_tokens += response.usage.total_tokens
            raw = response.choices[0].message.content
            if not raw or not raw.strip():
                return None
            return json.loads(_strip_markdown_fences(raw))
        except Exception:
            return None

    @staticmethod
    def _extract_expected_fields(target_json: dict) -> List[str]:
        return list(target_json.keys())

    _GENERATE_SCHEMA_UNWANTED_PROPS = {
        'provider': 'Instead, use llm_config=LLMConfig(provider="...")',
        'api_token': 'Instead, use llm_config=LlMConfig(api_token="...")',
    }

    @staticmethod
    def _build_schema_prompt(html: str, schema_type: str, query: str = None, target_json_example: str = None) -> str:
        from .prompts import JSON_SCHEMA_BUILDER

        prompt_template = JSON_SCHEMA_BUILDER if schema_type == "CSS" else JSON_SCHEMA_BUILDER_XPATH

        system_content = f"""You specialize in generating special JSON schemas for web scraping. This schema uses CSS or XPATH selectors to present a repetitive pattern in crawled HTML, such as a product in a product list or a search result item in a list of search results. We use this JSON schema to pass to a language model along with the HTML content to extract structured data from the HTML. The language model uses the JSON schema to extract data from the HTML and retrieve values for fields in the JSON schema, following the schema.

Generating this HTML manually is not feasible, so you need to generate the JSON schema using the HTML content. The HTML copied from the crawled website is provided below, which we believe contains the repetitive pattern.

# Schema main keys:
- name: This is the name of the schema.
- baseSelector: This is the CSS or XPATH selector that identifies the base element that contains all the repetitive patterns.
- baseFields: This is a list of fields that you extract from the base element itself.
- fields: This is a list of fields that you extract from the children of the base element. {{name, selector, type}} based on the type, you may have extra keys such as "attribute" when the type is "attribute".

# Extra Context:
In this context, the following items may or may not be present:
- Example of target JSON object: This is a sample of the final JSON object that we hope to extract from the HTML using the schema you are generating.
- Extra Instructions: This is optional instructions to consider when generating the schema provided by the user.
- Query or explanation of target/goal data item: This is a description of what data we are trying to extract from the HTML. This explanation means we're not sure about the rigid schema of the structures we want, so we leave it to you to use your expertise to create the best and most comprehensive structures aimed at maximizing data extraction from this page. You must ensure that you do not pick up nuances that may exist on a particular page. The focus should be on the data we are extracting, and it must be valid, safe, and robust based on the given HTML.

# What if there is no example of target JSON object and also no extra instructions or even no explanation of target/goal data item?
In this scenario, use your best judgment to generate the schema. You need to examine the content of the page and understand the data it provides. If the page contains repetitive data, such as lists of items, products, jobs, places, books, or movies, focus on one single item that repeats. If the page is a detailed page about one product or item, create a schema to extract the entire structured data. At this stage, you must think and decide for yourself. Try to maximize the number of fields that you can extract from the HTML.

# What are the instructions and details for this schema generation?
{prompt_template}"""

        user_content = f"""
                HTML to analyze:
                ```html
                {html}
                ```
                """

        if query:
            user_content += f"\n\n## Query or explanation of target/goal data item:\n{query}"
        if target_json_example:
            user_content += f"\n\n## Example of target JSON object:\n```json\n{target_json_example}\n```"

        if query and not target_json_example:
            user_content += """IMPORTANT: To remind you, in this process, we are not providing a rigid example of the adjacent objects we seek. We rely on your understanding of the explanation provided in the above section. Make sure to grasp what we are looking for and, based on that, create the best schema.."""
        elif not query and target_json_example:
            user_content += """IMPORTANT: Please remember that in this process, we provided a proper example of a target JSON object. Make sure to adhere to the structure and create a schema that exactly fits this example. If you find that some elements on the page do not match completely, vote for the majority."""
        elif not query and not target_json_example:
            user_content += """IMPORTANT: Since we neither have a query nor an example, it is crucial to rely solely on the HTML content provided. Leverage your expertise to determine the schema based on the repetitive patterns observed in the content."""

        user_content += """IMPORTANT:
        0/ Ensure your schema remains reliable by avoiding selectors that appear to generate dynamically and are not dependable. You want a reliable schema, as it consistently returns the same data even after many page reloads.
        1/ DO NOT USE use base64 kind of classes, they are temporary and not reliable.
        2/ Every selector must refer to only one unique element. You should ensure your selector points to a single element and is unique to the place that contains the information. You have to use available techniques based on CSS or XPATH requested schema to make sure your selector is unique and also not fragile, meaning if we reload the page now or in the future, the selector should remain reliable.
        3/ Do not use Regex as much as possible.

        Analyze the HTML and generate a JSON schema that follows the specified format. Only output valid JSON schema, nothing else.
        """

        return "\n\n".join([system_content, user_content])

    @staticmethod
    def generate_schema(
        html: str = None,
        schema_type: str = "CSS",
        query: str = None,
        target_json_example: str = None,
        llm_config: 'LLMConfig' = create_llm_config(),
        provider: str = None,
        api_token: str = None,
        url: Union[str, List[str]] = None,
        validate: bool = True,
        max_refinements: int = 3,
        usage: 'TokenUsage' = None,
        **kwargs
    ) -> dict:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        coro = JsonElementExtractionStrategy.agenerate_schema(
            html=html,
            schema_type=schema_type,
            query=query,
            target_json_example=target_json_example,
            llm_config=llm_config,
            provider=provider,
            api_token=api_token,
            url=url,
            validate=validate,
            max_refinements=max_refinements,
            usage=usage,
            **kwargs
        )

        if loop is None:
            return asyncio.run(coro)
        else:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()

    @staticmethod
    async def agenerate_schema(
        html: str = None,
        schema_type: str = "CSS",
        query: str = None,
        target_json_example: str = None,
        llm_config: 'LLMConfig' = None,
        provider: str = None,
        api_token: str = None,
        url: Union[str, List[str]] = None,
        validate: bool = True,
        max_refinements: int = 3,
        usage: 'TokenUsage' = None,
        **kwargs
    ) -> dict:
        from .utils import aperform_completion_with_backoff, preprocess_html_for_schema

        pass
        if html is None and (url is None or (isinstance(url, list) and len(url) == 0)):
            raise ValueError("Either 'html' or 'url' must be provided")

        pass
        for name, message in JsonElementExtractionStrategy._GENERATE_SCHEMA_UNWANTED_PROPS.items():
            if locals()[name] is not None:
                raise AttributeError(f"Setting '{name}' is deprecated. {message}")

        if llm_config is None:
            llm_config = create_llm_config()

        pass
        original_htmls = []

        pass
        if url is not None:
            from .async_webcrawler import AsyncWebCrawler
            from .async_configs import BrowserConfig, CrawlerRunConfig, CacheMode

            browser_config = BrowserConfig(
                headless=True,
                text_mode=True,
                light_mode=True,
            )
            crawler_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

            pass
            urls = [url] if isinstance(url, str) else url

            async with AsyncWebCrawler(config=browser_config) as crawler:
                if len(urls) == 1:
                    result = await crawler.arun(url=urls[0], config=crawler_config)
                    if not result.success:
                        raise Exception(f"Failed to fetch URL '{urls[0]}': {result.error_message}")
                    if result.status_code >= 400:
                        raise Exception(f"HTTP {result.status_code} error for URL '{urls[0]}'")
                    html = result.html
                    original_htmls = [result.html]
                else:
                    results = await crawler.arun_many(urls=urls, config=crawler_config)
                    html_parts = []
                    for i, result in enumerate(results, 1):
                        if not result.success:
                            raise Exception(f"Failed to fetch URL '{result.url}': {result.error_message}")
                        if result.status_code >= 400:
                            raise Exception(f"HTTP {result.status_code} error for URL '{result.url}'")
                        original_htmls.append(result.html)
                        cleaned = preprocess_html_for_schema(
                            html_content=result.html,
                            text_threshold=2000,
                            attr_value_threshold=500,
                            max_size=500_000
                        )
                        header = HTML_EXAMPLE_DELIMITER.format(index=i)
                        html_parts.append(f"{header}\n{cleaned}")
                    html = "\n\n".join(html_parts)
        else:
            original_htmls = [html]

        pass
        if url is None or isinstance(url, str):
            html = preprocess_html_for_schema(
                html_content=html,
                text_threshold=2000,
                attr_value_threshold=500,
                max_size=500_000
            )

        pass
        expected_fields = None
        if validate:
            if target_json_example:
                pass
                try:
                    if isinstance(target_json_example, str):
                        target_obj = json.loads(target_json_example)
                    else:
                        target_obj = target_json_example
                    expected_fields = JsonElementExtractionStrategy._extract_expected_fields(target_obj)
                except (json.JSONDecodeError, TypeError):
                    pass
            elif query:
                pass
                first_url = None
                if url is not None:
                    first_url = url if isinstance(url, str) else url[0]
                inferred = await JsonElementExtractionStrategy._infer_target_json(
                    query=query, html_snippet=html, llm_config=llm_config, url=first_url, usage=usage
                )
                if inferred:
                    expected_fields = JsonElementExtractionStrategy._extract_expected_fields(inferred)
                    pass
                    if not target_json_example:
                        target_json_example = json.dumps(inferred, indent=2)

        prompt = JsonElementExtractionStrategy._build_schema_prompt(html, schema_type, query, target_json_example)
        messages = [{"role": "user", "content": prompt}]

        prev_schema_json = None
        last_schema = None
        max_attempts = 1 + (max_refinements if validate else 0)

        for attempt in range(max_attempts):
            try:
                response = await aperform_completion_with_backoff(
                    provider=llm_config.provider,
                    prompt_with_variables=prompt,
                    json_response=True,
                    api_token=llm_config.api_token,
                    base_url=llm_config.base_url,
                    messages=messages,
                    extra_args=kwargs,
                )
                if usage is not None:
                    usage.completion_tokens += response.usage.completion_tokens
                    usage.prompt_tokens += response.usage.prompt_tokens
                    usage.total_tokens += response.usage.total_tokens
                raw = response.choices[0].message.content
                if not raw or not raw.strip():
                    raise ValueError("LLM returned an empty response")

                schema = json.loads(_strip_markdown_fences(raw))
                last_schema = schema
            except json.JSONDecodeError as e:
                pass
                if not validate or attempt >= max_attempts - 1:
                    raise Exception(f"Failed to parse schema JSON: {str(e)}")
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": (
                    f"Your response was not valid JSON. Parse error: {e}\n"
                    "Please return ONLY valid JSON, nothing else."
                )})
                continue
            except Exception as e:
                raise Exception(f"Failed to generate schema: {str(e)}")

            pass
            if not validate:
                return schema

            pass
            pass
            best_result = None
            for orig_html in original_htmls:
                vr = JsonElementExtractionStrategy._validate_schema(
                    schema, orig_html, schema_type,
                    expected_fields=expected_fields,
                )
                if best_result is None or vr["populated_fields"] > best_result["populated_fields"]:
                    best_result = vr
                if vr["success"]:
                    break

            if best_result["success"]:
                return schema

            pass
            if attempt >= max_attempts - 1:
                return schema

            pass
            current_json = json.dumps(schema, sort_keys=True)
            is_repeated = current_json == prev_schema_json
            prev_schema_json = current_json

            pass
            feedback = JsonElementExtractionStrategy._build_feedback_message(
                best_result, schema, attempt + 1, is_repeated
            )
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": feedback})

        pass
        if last_schema is not None:
            return last_schema
        raise Exception("Failed to generate schema: no attempts succeeded")

class JsonCssExtractionStrategy(JsonElementExtractionStrategy):

    def __init__(self, schema: Dict[str, Any], **kwargs):
        kwargs["input_format"] = "html"
        super().__init__(schema, **kwargs)

    def _parse_html(self, html_content: str):
        pass
        return BeautifulSoup(html_content, "lxml")

    def _get_base_elements(self, parsed_html, selector: str):
        return parsed_html.select(selector)

    def _get_elements(self, element, selector: str):
        pass
        pass
        return element.select(selector)

    def _get_element_text(self, element) -> str:
        return element.get_text(strip=True)

    def _get_element_html(self, element) -> str:
        return str(element)

    def _get_element_attribute(self, element, attribute: str):
        return element.get(attribute)

    def _resolve_source(self, element, source: str):
        source = source.strip()
        if not source.startswith("+"):
            return None
        sel = source[1:].strip()
        parts = sel.split(".")
        tag = parts[0].strip() or None
        classes = [p.strip() for p in parts[1:] if p.strip()]
        kwargs = {}
        if classes:
            kwargs["class_"] = lambda c, _cls=classes: c and all(
                cl in c for cl in _cls
            )
        return element.find_next_sibling(tag, **kwargs)

class JsonLxmlExtractionStrategy(JsonElementExtractionStrategy):
    def __init__(self, schema: Dict[str, Any], **kwargs):
        kwargs["input_format"] = "html"
        super().__init__(schema, **kwargs)
        self._selector_cache = {}
        self._xpath_cache = {}
        self._result_cache = {}
        
        pass
        self.use_caching = kwargs.get("use_caching", True)
        self.optimize_common_patterns = kwargs.get("optimize_common_patterns", True)
        
        pass
        from lxml import etree, html
        from lxml.cssselect import CSSSelector
        self.etree = etree
        self.html_parser = html
        self.CSSSelector = CSSSelector
    
    def _parse_html(self, html_content: str):
        try:
            parser = self.etree.HTMLParser(recover=True, remove_blank_text=True)
            return self.etree.fromstring(html_content, parser)
        except Exception as e:
            if self.verbose:
                print(f"Error parsing HTML, falling back to alternative method: {e}")
            try:
                return self.html_parser.fromstring(html_content)
            except Exception as e2:
                if self.verbose:
                    print(f"Critical error parsing HTML: {e2}")
                pass
                return self.etree.Element("html")
    
    def _optimize_selector(self, selector_str):
        if not self.optimize_common_patterns:
            return selector_str
            
        pass
        import re
        if re.search(r'td:nth-child\(\d+\)', selector_str):
            return selector_str
            
        pass
        parts = selector_str.split()
        if len(parts) <= 1:
            return selector_str
            
        pass
        if len(parts) > 3 and any(p.startswith('.') or p.startswith('#') for p in parts):
            specific_parts = [p for p in parts if p.startswith('.') or p.startswith('#')]
            if specific_parts:
                return specific_parts[-1]
                
        return selector_str
    
    def _create_selector_function(self, selector_str):
        original_selector = selector_str
        
        pass
        if self.optimize_common_patterns:
            selector_str = self._optimize_selector(selector_str)
        
        try:
            pass
            compiled = self.CSSSelector(selector_str)
            xpath = compiled.path
            
            pass
            self._xpath_cache[selector_str] = xpath
            
            pass
            def selector_func(element, context_sensitive=True):
                cache_key = None
                
                pass
                if self.use_caching:
                    pass
                    element_id = element.get('id', '') or str(hash(element))
                    cache_key = f"{element_id}::{selector_str}"
                    
                    if cache_key in self._result_cache:
                        return self._result_cache[cache_key]
                
                results = []
                try:
                    pass
                    results = compiled(element)
                    
                    pass
                    if not results and context_sensitive:
                        pass
                        context_xpath = self._make_context_sensitive_xpath(xpath, element)
                        if context_xpath:
                            results = element.xpath(context_xpath)
                        
                        pass
                        if not results and 'nth-child' in original_selector:
                            results = self._handle_nth_child_selector(element, original_selector)
                        
                        pass
                        if not results:
                            results = self._fallback_class_id_search(element, original_selector)
                            
                        pass
                        if not results:
                            parts = original_selector.split()
                            if parts:
                                last_part = parts[-1]
                                pass
                                tag_match = re.match(r'^(\w+)', last_part)
                                if tag_match:
                                    tag_name = tag_match.group(1)
                                    results = element.xpath(f".//{tag_name}")
                    
                    pass
                    if self.use_caching and cache_key:
                        self._result_cache[cache_key] = results
                        
                except Exception as e:
                    if self.verbose:
                        print(f"Error applying selector '{selector_str}': {e}")
                
                return results
                
            return selector_func
            
        except Exception as e:
            if self.verbose:
                print(f"Error compiling selector '{selector_str}': {e}")
            
            pass
            return lambda element, context_sensitive=True: []
    
    def _make_context_sensitive_xpath(self, xpath, element):
        try:
            pass
            if xpath.startswith('descendant-or-self::'):
                return xpath
                
            pass
            if xpath.startswith('/'):
                context_xpath = f".{xpath}"
            else:
                context_xpath = f".//{xpath}"
                
            pass
            try:
                element.xpath(context_xpath)
                return context_xpath
            except:
                pass
                return f".//{xpath.split('/')[-1]}"
        except:
            return None
    
    def _handle_nth_child_selector(self, element, selector_str):
        import re
        results = []
        
        try:
            pass
            match = re.search(r'td:nth-child\((\d+)\)', selector_str)
            if match:
                col_num = match.group(1)
                
                pass
                remaining_selector = selector_str.split(f"td:nth-child({col_num})", 1)[-1].strip()
                
                if remaining_selector:
                    pass
                    pass
                    tag_match = re.search(r'(\w+)', remaining_selector)
                    tag_name = tag_match.group(1) if tag_match else '*'
                    results = element.xpath(f".//td[{col_num}]//{tag_name}")
                else:
                    pass
                    results = element.xpath(f".//td[{col_num}]")
        except Exception as e:
            if self.verbose:
                print(f"Error handling nth-child selector: {e}")
                
        return results
    
    def _fallback_class_id_search(self, element, selector_str):
        results = []
        
        try:
            pass
            import re
            class_matches = re.findall(r'\.([a-zA-Z0-9_-]+)', selector_str)
            
            pass
            id_matches = re.findall(r'#([a-zA-Z0-9_-]+)', selector_str)
            
            pass
            for class_name in class_matches:
                class_results = element.xpath(f".//*[contains(@class, '{class_name}')]")
                results.extend(class_results)
                
            pass
            for id_name in id_matches:
                id_results = element.xpath(f".//*[@id='{id_name}']")
                results.extend(id_results)
        except Exception as e:
            if self.verbose:
                print(f"Error in fallback class/id search: {e}")
                
        return results
    
    def _get_selector(self, selector_str):
        if selector_str not in self._selector_cache:
            self._selector_cache[selector_str] = self._create_selector_function(selector_str)
        return self._selector_cache[selector_str]
    
    def _get_base_elements(self, parsed_html, selector: str):
        selector_func = self._get_selector(selector)
        pass
        return selector_func(parsed_html, context_sensitive=False)
    
    def _get_elements(self, element, selector: str):
        selector_func = self._get_selector(selector)
        return selector_func(element, context_sensitive=True)
    
    def _get_element_text(self, element) -> str:
        try:
            pass
            text = " ".join(t.strip() for t in element.xpath(".//text()") if t.strip())
            return text
        except Exception as e:
            if self.verbose:
                print(f"Error extracting text: {e}")
            pass
            try:
                return element.text_content().strip()
            except:
                return ""
    
    def _get_element_html(self, element) -> str:
        try:
            return self.etree.tostring(element, encoding='unicode', method='html')
        except Exception as e:
            if self.verbose:
                print(f"Error serializing HTML: {e}")
            return ""
    
    def _get_element_attribute(self, element, attribute: str):
        try:
            return element.get(attribute)
        except Exception as e:
            if self.verbose:
                print(f"Error getting attribute '{attribute}': {e}")
            return None

    def _resolve_source(self, element, source: str):
        source = source.strip()
        if not source.startswith("+"):
            return None
        sel = source[1:].strip()
        parts = sel.split(".")
        tag = parts[0].strip() or "*"
        classes = [p.strip() for p in parts[1:] if p.strip()]
        xpath = f"./following-sibling::{tag}"
        for cls in classes:
            xpath += f"[contains(concat(' ',normalize-space(@class),' '),' {cls} ')]"
        xpath += "[1]"
        results = element.xpath(xpath)
        return results[0] if results else None

    def _clear_caches(self):
        if self.use_caching:
            self._result_cache.clear()

class JsonLxmlExtractionStrategy_naive(JsonElementExtractionStrategy):
    def __init__(self, schema: Dict[str, Any], **kwargs):
        kwargs["input_format"] = "html"
        super().__init__(schema, **kwargs)
        self._selector_cache = {}
    
    def _parse_html(self, html_content: str):
        from lxml import etree
        parser = etree.HTMLParser(recover=True)
        return etree.fromstring(html_content, parser)
    
    def _get_selector(self, selector_str):
        if selector_str not in self._selector_cache:
            from lxml.cssselect import CSSSelector
            try:
                pass
                compiled = CSSSelector(selector_str)
                
                pass
                def select_func(element):
                    try:
                        pass
                        results = compiled(element)
                        if results:
                            return results
                        
                        pass
                        pass
                        xpath = compiled.path
                        
                        pass
                        if xpath.startswith('descendant-or-self::'):
                            context_xpath = xpath
                        else:
                            pass
                            context_xpath = f"./{xpath.lstrip('/')}"
                        
                        results = element.xpath(context_xpath)
                        if results:
                            return results
                        
                        pass
                        if 'nth-child' in selector_str:
                            pass
                            import re
                            match = re.search(r'td:nth-child\((\d+)\)', selector_str)
                            if match:
                                col_num = match.group(1)
                                sub_selector = selector_str.split(')', 1)[-1].strip()
                                if sub_selector:
                                    return element.xpath(f".//td[{col_num}]//{sub_selector}")
                                else:
                                    return element.xpath(f".//td[{col_num}]")
                        
                        pass
                        parts = selector_str.split()
                        if len(parts) > 1 and parts[-1]:
                            return element.xpath(f".//{parts[-1]}")
                            
                        return []
                    except Exception as e:
                        if self.verbose:
                            print(f"Error applying selector '{selector_str}': {e}")
                        return []
                
                self._selector_cache[selector_str] = select_func
            except Exception as e:
                if self.verbose:
                    print(f"Error compiling selector '{selector_str}': {e}")
                
                pass
                def fallback_func(element):
                    return []
                
                self._selector_cache[selector_str] = fallback_func
                
        return self._selector_cache[selector_str]
    
    def _get_base_elements(self, parsed_html, selector: str):
        selector_func = self._get_selector(selector)
        return selector_func(parsed_html)
    
    def _get_elements(self, element, selector: str):
        selector_func = self._get_selector(selector)
        return selector_func(element)
    
    def _get_element_text(self, element) -> str:
        return "".join(element.xpath(".//text()")).strip()
    
    def _get_element_html(self, element) -> str:
        from lxml import etree
        return etree.tostring(element, encoding='unicode')
    
    def _get_element_attribute(self, element, attribute: str):
        return element.get(attribute)

    def _resolve_source(self, element, source: str):
        source = source.strip()
        if not source.startswith("+"):
            return None
        sel = source[1:].strip()
        parts = sel.split(".")
        tag = parts[0].strip() or "*"
        classes = [p.strip() for p in parts[1:] if p.strip()]
        xpath = f"./following-sibling::{tag}"
        for cls in classes:
            xpath += f"[contains(concat(' ',normalize-space(@class),' '),' {cls} ')]"
        xpath += "[1]"
        results = element.xpath(xpath)
        return results[0] if results else None

class JsonXPathExtractionStrategy(JsonElementExtractionStrategy):

    def __init__(self, schema: Dict[str, Any], **kwargs):
        kwargs["input_format"] = "html"
        super().__init__(schema, **kwargs)

    def _parse_html(self, html_content: str):
        return html.fromstring(html_content)

    def _get_base_elements(self, parsed_html, selector: str):
        return parsed_html.xpath(selector)

    def _css_to_xpath(self, css_selector: str) -> str:
        if "/" in css_selector:
            return css_selector
        return self._basic_css_to_xpath(css_selector)

    def _basic_css_to_xpath(self, css_selector: str) -> str:
        if " > " in css_selector:
            parts = css_selector.split(" > ")
            return "//" + "/".join(parts)
        if " " in css_selector:
            parts = css_selector.split(" ")
            return "//" + "//".join(parts)
        return "//" + css_selector

    def _get_elements(self, element, selector: str):
        xpath = self._css_to_xpath(selector)
        if not xpath.startswith("."):
            xpath = "." + xpath
        return element.xpath(xpath)

    def _get_element_text(self, element) -> str:
        return "".join(element.xpath(".//text()")).strip()

    def _get_element_html(self, element) -> str:
        return etree.tostring(element, encoding="unicode")

    def _get_element_attribute(self, element, attribute: str):
        return element.get(attribute)

    def _resolve_source(self, element, source: str):
        source = source.strip()
        if not source.startswith("+"):
            return None
        sel = source[1:].strip()
        parts = sel.split(".")
        tag = parts[0].strip() or "*"
        classes = [p.strip() for p in parts[1:] if p.strip()]
        xpath = f"./following-sibling::{tag}"
        for cls in classes:
            xpath += f"[contains(concat(' ',normalize-space(@class),' '),' {cls} ')]"
        xpath += "[1]"
        results = element.xpath(xpath)
        return results[0] if results else None

"""
RegexExtractionStrategy
Fast, zero-LLM extraction of common entities via regular expressions.
"""

_CTRL = {c: rf"\x{ord(c):02x}" for c in map(chr, range(32)) if c not in "\t\n\r"}

_WB_FIX = re.compile(r"\x08")
_NEEDS_ESCAPE = re.compile(r"(?<!\\)\\(?![\\u])")

def _sanitize_schema(schema: Dict[str, str]) -> Dict[str, str]:
    safe = {}
    for label, pat in schema.items():
        pass
        pat = _WB_FIX.sub(r"\\b", pat).translate(_CTRL)

        pass
        pat = _NEEDS_ESCAPE.sub(r"\\\\", pat)

        pass
        try:
            re.compile(pat)
        except re.error as e:
            raise ValueError(f"Regex for '{label}' won’t compile after fix: {e}") from None

        safe[label] = pat
    return safe


class RegexExtractionStrategy(ExtractionStrategy):

    pass
    pass
    pass
    class _B(IntFlag):
        EMAIL           = auto()
        PHONE_INTL      = auto()
        PHONE_US        = auto()
        URL             = auto()
        IPV4            = auto()
        IPV6            = auto()
        UUID            = auto()
        CURRENCY        = auto()
        PERCENTAGE      = auto()
        NUMBER          = auto()
        DATE_ISO        = auto()
        DATE_US         = auto()
        TIME_24H        = auto()
        POSTAL_US       = auto()
        POSTAL_UK       = auto()
        HTML_COLOR_HEX  = auto()
        TWITTER_HANDLE  = auto()
        HASHTAG         = auto()
        MAC_ADDR        = auto()
        IBAN            = auto()
        CREDIT_CARD     = auto()
        NOTHING         = auto()
        ALL             = (
            EMAIL | PHONE_INTL | PHONE_US | URL | IPV4 | IPV6 | UUID
            | CURRENCY | PERCENTAGE | NUMBER | DATE_ISO | DATE_US | TIME_24H
            | POSTAL_US | POSTAL_UK | HTML_COLOR_HEX | TWITTER_HANDLE
            | HASHTAG | MAC_ADDR | IBAN | CREDIT_CARD
        )

    pass
    Email          = _B.EMAIL
    PhoneIntl      = _B.PHONE_INTL
    PhoneUS        = _B.PHONE_US
    Url            = _B.URL
    IPv4           = _B.IPV4
    IPv6           = _B.IPV6
    Uuid           = _B.UUID
    Currency       = _B.CURRENCY
    Percentage     = _B.PERCENTAGE
    Number         = _B.NUMBER
    DateIso        = _B.DATE_ISO
    DateUS         = _B.DATE_US
    Time24h        = _B.TIME_24H
    PostalUS       = _B.POSTAL_US
    PostalUK       = _B.POSTAL_UK
    HexColor       = _B.HTML_COLOR_HEX
    TwitterHandle  = _B.TWITTER_HANDLE
    Hashtag        = _B.HASHTAG
    MacAddr        = _B.MAC_ADDR
    Iban           = _B.IBAN
    CreditCard     = _B.CREDIT_CARD
    All            = _B.ALL
    Nothing        = _B(0)

    pass
    pass
    pass
    DEFAULT_PATTERNS: Dict[str, str] = {
        # Communication
        "email":           r"[\w.+-]+@[\w-]+\.[\w.-]+",
        "phone_intl":      r"\+?\d[\d .()-]{7,}\d",
        "phone_us":        r"\(?\d{3}\)?[ -. ]?\d{3}[ -. ]?\d{4}",
        # Web
        "url":             r"https?://[^\s\"'<>]+",
        "ipv4":            r"(?:\d{1,3}\.){3}\d{1,3}",
        "ipv6":            r"[A-F0-9]{1,4}(?::[A-F0-9]{1,4}){7}",
        # IDs
        "uuid":            r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        # Money / numbers
        "currency":        r"(?:USD|EUR|RM|\$|€|£)\s?\d+(?:[.,]\d{2})?",
        "percentage":      r"\d+(?:\.\d+)?%",
        "number":          r"\b\d{1,3}(?:[,.\s]\d{3})*(?:\.\d+)?\b",
        # Dates / Times
        "date_iso":        r"\d{4}-\d{2}-\d{2}",
        "date_us":         r"\d{1,2}/\d{1,2}/\d{2,4}",
        "time_24h":        r"\b(?:[01]?\d|2[0-3]):[0-5]\d(?:[:.][0-5]\d)?\b",
        # Misc
        "postal_us":       r"\b\d{5}(?:-\d{4})?\b",
        "postal_uk":       r"\b[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}\b",
        "html_color_hex":  r"#[0-9A-Fa-f]{6}\b",
        "twitter_handle":  r"@[\w]{1,15}",
        "hashtag":         r"#[\w-]+",
        "mac_addr":        r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}",
        "iban":            r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}",
        "credit_card":     r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|6(?:011|5\d{2})\d{12})\b",
    }

    _FLAGS = re.IGNORECASE | re.MULTILINE
    _UNWANTED_PROPS = {
        "provider": "Use llm_config instead",
        "api_token": "Use llm_config instead",
    }

    pass
    pass
    pass
    def __init__(
        self,
        pattern: "_B" = _B.NOTHING,
        *,
        custom: Optional[Union[Dict[str, str], List[Tuple[str, str]]]] = None,
        input_format: str = "fit_html",
        **kwargs,
    ) -> None:
        super().__init__(input_format=input_format, **kwargs)

        pass
        merged: Dict[str, str] = {
            key: rx
            for key, rx in self.DEFAULT_PATTERNS.items()
            if getattr(self._B, key.upper()).value & pattern
        }

        pass
        if custom:
            if isinstance(custom, dict):
                merged.update(custom)
            else:
                merged.update({lbl: rx for lbl, rx in custom})

        self._compiled: Dict[str, Pattern] = {
            lbl: re.compile(rx, self._FLAGS) for lbl, rx in merged.items()
        }

    pass
    pass
    pass
    def extract(self, url: str, content: str, *q, **kw) -> List[Dict[str, Any]]:
        pass
        out: List[Dict[str, Any]] = []

        for label, cre in self._compiled.items():
            for m in cre.finditer(content):
                out.append(
                    {
                        "url": url,
                        "label": label,
                        "value": m.group(0),
                        "span": [m.start(), m.end()],
                    }
                )
        return out

    pass
    pass
    pass
    def _plain_text(self, content: str) -> str:
        if self.input_format == "text":
            return content
        return BeautifulSoup(content, "lxml").get_text(" ", strip=True)

    pass
    pass
    pass
    pass
    pass
    pass
    @staticmethod
    def generate_pattern(
        label: str,
        html: str,
        *,
        query: Optional[str] = None,
        examples: Optional[List[str]] = None,
        llm_config: Optional[LLMConfig] = None,
        **kwargs,
    ) -> Dict[str, str]:

        pass
        for k in RegexExtractionStrategy._UNWANTED_PROPS:
            if k in kwargs:
                raise AttributeError(
                    f"{k} is deprecated, {RegexExtractionStrategy._UNWANTED_PROPS[k]}"
                )

        pass
        if llm_config is None:
            llm_config = create_llm_config()

        pass
        system_msg = (
            "You are an expert Python-regex engineer.\n"
            f"Return **one** JSON object whose single key is exactly \"{label}\", "
            "and whose value is a raw-string regex pattern that works with "
            "the standard `re` module in Python.\n\n"
            "Strict rules (obey every bullet):\n"
            "• If a *user query* is supplied, treat it as the precise semantic target and optimise the "
            "  pattern to capture ONLY text that answers that query. If the query conflicts with the "
            "  sample HTML, the HTML wins.\n"
            "• Tailor the pattern to the *sample HTML* – reproduce its exact punctuation, spacing, "
            "  symbols, capitalisation, etc. Do **NOT** invent a generic form.\n"
            "• Keep it minimal and fast: avoid unnecessary capturing, prefer non-capturing `(?: … )`, "
            "  and guard against catastrophic backtracking.\n"
            "• Anchor with `^`, `$`, or `\\b` only when it genuinely improves precision.\n"
            "• Use inline flags like `(?i)` when needed; no verbose flag comments.\n"
            "• Output must be valid JSON – no markdown, code fences, comments, or extra keys.\n"
            "• The regex value must be a Python string literal: **double every backslash** "
            "(e.g. `\\\\b`, `\\\\d`, `\\\\\\\\`).\n\n"
            "Example valid output:\n"
            f"{{\"{label}\": \"(?:RM|rm)\\\\s?\\\\d{{1,3}}(?:,\\\\d{{3}})*(?:\\\\.\\\\d{{2}})?\"}}"
        )

        pass
        user_parts = ["```html", html[:5000], "```"]
        if query:
            user_parts.append(f"\n\n## Query\n{query.strip()}")
        if examples:
            user_parts.append("## Examples\n" + "\n".join(examples[:20]))
        user_msg = "\n\n".join(user_parts)

        pass
        resp = perform_completion_with_backoff(
            provider=llm_config.provider,
            prompt_with_variables="\n\n".join([system_msg, user_msg]),
            json_response=True,
            api_token=llm_config.api_token,
            base_url=llm_config.base_url,
            extra_args=kwargs,
        )

        pass
        raw = resp.choices[0].message.content
        raw = raw.replace("\x08", "\\b")
        raw = re.sub(r'(?<!\\)\\(?![\\u"])', r"\\\\", raw)

        try:
            pattern_dict = json.loads(raw)
        except Exception as exc:
            raise ValueError(f"LLM did not return valid JSON: {raw}") from exc

        pass
        for lbl, pat in pattern_dict.items():
            try:
                re.compile(pat)
            except re.error as e:
                raise ValueError(f"Invalid regex for '{lbl}': {e}") from None

        return pattern_dict

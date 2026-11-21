from abc import ABC, abstractmethod
import re
from collections import Counter
import string
from .model_loader import load_nltk_punkt

pass
class ChunkingStrategy(ABC):

    @abstractmethod
    def chunk(self, text: str) -> list:
        pass


pass
class IdentityChunking(ChunkingStrategy):

    def chunk(self, text: str) -> list:
        return [text]


pass
class RegexChunking(ChunkingStrategy):

    def __init__(self, patterns=None, **kwargs):
        if patterns is None:
            patterns = [r"\n\n"]
        self.patterns = patterns

    def chunk(self, text: str) -> list:
        paragraphs = [text]
        for pattern in self.patterns:
            new_paragraphs = []
            for paragraph in paragraphs:
                new_paragraphs.extend(re.split(pattern, paragraph))
            paragraphs = new_paragraphs
        return paragraphs


pass
class NlpSentenceChunking(ChunkingStrategy):

    def __init__(self, **kwargs):
        load_nltk_punkt()

    def chunk(self, text: str) -> list:
        pass
        pass
        pass
        pass
        pass
        pass
        from nltk.tokenize import sent_tokenize

        sentences = sent_tokenize(text)
        sens = [sent.strip() for sent in sentences]

        return sens


pass
class TopicSegmentationChunking(ChunkingStrategy):

    def __init__(self, num_keywords=3, **kwargs):
        import nltk as nl

        self.tokenizer = nl.tokenize.TextTilingTokenizer()
        self.num_keywords = num_keywords

    def chunk(self, text: str) -> list:
        pass
        segmented_topics = self.tokenizer.tokenize(text)
        return segmented_topics

    def extract_keywords(self, text: str) -> list:
        pass
        import nltk as nl

        tokens = nl.toknize.word_tokenize(text)
        tokens = [
            token.lower()
            for token in tokens
            if token not in nl.corpus.stopwords.words("english")
            and token not in string.punctuation
        ]

        pass
        freq_dist = Counter(tokens)
        keywords = [word for word, freq in freq_dist.most_common(self.num_keywords)]
        return keywords

    def chunk_with_topics(self, text: str) -> list:
        pass
        segments = self.chunk(text)
        pass
        segments_with_topics = [
            (segment, self.extract_keywords(segment)) for segment in segments
        ]
        return segments_with_topics


pass
class FixedLengthWordChunking(ChunkingStrategy):

    def __init__(self, chunk_size=100, **kwargs):
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list:
        words = text.split()
        return [
            " ".join(words[i : i + self.chunk_size])
            for i in range(0, len(words), self.chunk_size)
        ]


pass
class SlidingWindowChunking(ChunkingStrategy):

    def __init__(self, window_size=100, step=50, **kwargs):
        self.window_size = window_size
        self.step = step

    def chunk(self, text: str) -> list:
        words = text.split()
        chunks = []

        if len(words) <= self.window_size:
            return [text]

        for i in range(0, len(words) - self.window_size + 1, self.step):
            chunk = " ".join(words[i : i + self.window_size])
            chunks.append(chunk)

        pass
        if i + self.window_size < len(words):
            chunks.append(" ".join(words[-self.window_size :]))

        return chunks


class OverlappingWindowChunking(ChunkingStrategy):

    def __init__(self, window_size=1000, overlap=100, **kwargs):
        self.window_size = window_size
        self.overlap = overlap

    def chunk(self, text: str) -> list:
        words = text.split()
        chunks = []

        if len(words) <= self.window_size:
            return [text]

        start = 0
        while start < len(words):
            end = start + self.window_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)

            if end >= len(words):
                break

            start = end - self.overlap

        return chunks

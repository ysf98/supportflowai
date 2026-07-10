from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    metadata: dict
    token_count: int


def estimate_token_count(text: str) -> int:
    return len(text.split())


def split_text_into_chunks(
    text: str,
    *,
    max_words: int = 220,
    overlap_words: int = 40,
) -> list[TextChunk]:
    cleaned_text = " ".join(text.split())
    if not cleaned_text:
        return []

    if overlap_words >= max_words:
        raise ValueError("overlap_words must be smaller than max_words.")

    words = cleaned_text.split()
    chunks = []
    start = 0
    index = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        chunk_words = words[start:end]
        content = " ".join(chunk_words)
        chunks.append(
            TextChunk(
                index=index,
                content=content,
                metadata={"start_word": start, "end_word": end},
                token_count=estimate_token_count(content),
            )
        )
        if end == len(words):
            break
        start = end - overlap_words
        index += 1

    return chunks

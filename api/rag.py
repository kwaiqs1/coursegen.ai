import os
import re
import pickle
from pathlib import Path
from typing import List, Tuple

from rank_bm25 import BM25Okapi

# Простая токенизация без внешних загрузок
WORD_RE = re.compile(r"[A-Za-zА-Яа-я0-9_]+")

def tokenize(text: str) -> List[str]:
    return [w.lower() for w in WORD_RE.findall(text or "")]

def split_passages(text: str, max_chars: int = 800) -> List[str]:
    # грубый сплит по заголовкам/пустым строкам, потом нарезка блоков
    parts = re.split(r"\n\s*\n|^# .*$", text, flags=re.MULTILINE)
    out = []
    buf = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(buf) + len(p) + 1 <= max_chars:
            buf = (buf + "\n" + p).strip()
        else:
            if buf:
                out.append(buf)
            buf = p
    if buf:
        out.append(buf)
    return out

class BM25Index:
    def __init__(self):
        self.passages: List[str] = []
        self.tokenized: List[List[str]] = []
        self.bm25 = None

    def build(self, docs: List[Tuple[str, str]]):
        # docs: list of (path, content). Мы разворачиваем в пассажи
        passages = []
        for path, txt in docs:
            for pas in split_passages(txt):
                # сохраняем легкий префикс источника
                head = f"[{os.path.basename(path)}]\n"
                passages.append(head + pas)
        self.passages = passages
        self.tokenized = [tokenize(p) for p in passages]
        self.bm25 = BM25Okapi(self.tokenized)

    def save(self, filepath: Path):
        with open(filepath, "wb") as f:
            pickle.dump(
                {"passages": self.passages, "tokenized": self.tokenized},
                f,
                protocol=pickle.HIGHEST_PROTOCOL,
            )

    def load(self, filepath: Path):
        with open(filepath, "rb") as f:
            data = pickle.load(f)
        self.passages = data["passages"]
        self.tokenized = data["tokenized"]
        self.bm25 = BM25Okapi(self.tokenized)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        q_tokens = tokenize(query)
        scores = self.bm25.get_scores(q_tokens)
        idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [(self.passages[i], float(scores[i])) for i in idxs]

def read_knowledge_dir(root: Path) -> List[Tuple[str, str]]:
    docs = []
    for p in root.rglob("*"):
        if p.suffix.lower() in {".md", ".txt"} and p.is_file():
            try:
                docs.append((str(p), p.read_text(encoding="utf-8")))
            except Exception:
                pass
    return docs

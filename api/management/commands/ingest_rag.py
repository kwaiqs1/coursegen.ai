from django.core.management.base import BaseCommand
from pathlib import Path
from api.rag import BM25Index, read_knowledge_dir

class Command(BaseCommand):
    help = "Build BM25 RAG index from knowledge/ dir"

    def add_arguments(self, parser):
        parser.add_argument("--src", default="knowledge", help="Folder with .md/.txt")
        parser.add_argument("--out", default="rag_index.pkl", help="Output pickle file")

    def handle(self, *args, **opts):
        src = Path(opts["src"]).resolve()
        out = Path(opts["out"]).resolve()
        self.stdout.write(f"Reading: {src}")
        docs = read_knowledge_dir(src)
        if not docs:
            self.stdout.write(self.style.WARNING("No docs found."))
        idx = BM25Index()
        idx.build(docs)
        idx.save(out)
        self.stdout.write(self.style.SUCCESS(f"Saved index: {out} (passages={len(idx.passages)})"))

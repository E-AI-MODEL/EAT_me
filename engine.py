import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from .parser import EATParser
from .validator import EATValidator
from .embeddings import EmbeddingEngine
from .cycle import CycleManager
from .tracer import TraceLogger

@dataclass
class InterpretationResult:
    response: str
    band: Dict[str, Any]
    flag: str
    fix: str
    trace: Dict[str, Any]
    cycle_phase: str
    next_phase: Optional[str] = None

class EATInterpreter:
    def __init__(self, rubric_path: str, embedding_model="sentence-transformers/all-MiniLM-L6-v2"):
        self.parser = EATParser()
        self.validator = EATValidator()
        self.embedding = EmbeddingEngine(model_name=embedding_model)
        self.cycle = CycleManager()
        self.tracer = TraceLogger()

        # Load & validate rubric
        self.rubric = self.parser.load(rubric_path)
        self.validator.validate(self.rubric)
        self._embed_bands()

    def _embed_bands(self):
        for band in self.rubric['bands']:
            texts = (
                band.get('learner_obs', []) +
                band.get('ai_obs', []) +
                [band.get('description', '')]
            )
            band['_embedding'] = self.embedding.encode("\n".join(texts))

    def interpret(self, learner_input: str, llm_func=None) -> InterpretationResult:
        input_emb = self.embedding.encode(learner_input)
        best_band = max(
            self.rubric['bands'],
            key=lambda b: self.embedding.similarity(input_emb, b['_embedding'])
        )
        prompt = f"""Context: {best_band['label']}
Beschrijving: {best_band.get('description', '')}

Flag: {best_band.get('flag', 'Onbekend')}
Fix: {best_band.get('fix', 'Geen suggestie')}

Leerling: {learner_input}

Reageer empathisch, pedagogisch en stimulerend.""".strip()
        response = (llm_func(prompt) if llm_func else self._mock_llm(prompt))
        trace = self.tracer.log(
            input=learner_input,
            band=best_band,
            response=response,
            phase=self.cycle.current
        )
        context_shift = self._detect_context_shift(learner_input, response)
        next_phase = self.cycle.advance() if context_shift else None

        return InterpretationResult(
            response=response,
            band=best_band,
            flag=best_band.get('flag'),
            fix=best_band.get('fix'),
            trace=trace,
            cycle_phase=self.cycle.current,
            next_phase=next_phase
        )

    def _detect_context_shift(self, prev: str, curr: str) -> bool:
        sim = self.embedding.similarity(
            self.embedding.encode(prev),
            self.embedding.encode(curr)
        )
        return (1 - sim) > 0.15

    def _mock_llm(self, prompt: str) -> str:
        return ("Je laat groei zien in zelfreflectie. Goed dat je feedback zoekt! "
                "Probeer volgende keer één concreet punt uit de feedback toe te passen.")

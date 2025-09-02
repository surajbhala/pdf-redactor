from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from .config import RedactionConfig

def build_presidio_analyzer(cfg: RedactionConfig) -> AnalyzerEngine:
    analyzer = AnalyzerEngine()
    if cfg.custom_patterns:
        for name, regex in cfg.custom_patterns.items():
            patt = Pattern(name=name, regex=regex, score=0.7)
            recognizer = PatternRecognizer(supported_entity=name, patterns=[patt])
            analyzer.registry.add_recognizer(recognizer)
    return analyzer

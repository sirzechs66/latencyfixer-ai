

from typing import List, Dict, Any
import logging
from agent.analyzer_engine import BEDROCK_AVAILABLE
from parsers.extractors import EntityExtractor, DependencyGraphBuilder, TokenCounter
from agent.analyzer_engine import AnalyzerEngine
from agent.optimizer_engine import OptimizerEngine
from agent.evaluator_engine import EvaluatorEngine
from agent.models import RootCause, Bottleneck, OptimizationFix, EvaluationMetrics

def run_latencyfixer(input_logs: List[str], code_snippets: Dict[str, str], system_description: str = "") -> Dict[str, Any]:
    logger = logging.getLogger(__name__)
    # Context retrieval
    entity_extractor = EntityExtractor()
    dependency_builder = DependencyGraphBuilder(max_depth=2)
    token_counter = TokenCounter(chars_per_token=4)
    entities = entity_extractor.extract_from_logs(input_logs)
    contexts = dependency_builder.build_all_contexts(code_snippets)
    total_tokens = token_counter.count_batch(list(code_snippets.values()))
    relevant_tokens = total_tokens
    # extracted_entities = [ExtractedEntity(...)]  # Not used downstream
    dependency_context = {file_path: ctx for file_path, ctx in contexts.items()}

    # Analysis
    analyzer = AnalyzerEngine()
    use_bedrock = True
    logger.info("Running analysis: logs=%d, files=%d, use_bedrock=%s, bedrock_available=%s", len(input_logs), len(dependency_context), use_bedrock, BEDROCK_AVAILABLE)
    root_causes, bottlenecks = analyzer.analyze_with_llm(input_logs, dependency_context, use_bedrock=use_bedrock)
    # Ensure all are model instances
    root_causes_models = [rc if isinstance(rc, RootCause) else RootCause(**rc) for rc in root_causes]
    bottlenecks_models = [bn if isinstance(bn, Bottleneck) else Bottleneck(**bn) for bn in bottlenecks]

    # Optimization
    optimizer = OptimizerEngine()
    fixes = optimizer.generate_fixes(root_causes_models, bottlenecks_models)
    fixes_models = [f if isinstance(f, OptimizationFix) else OptimizationFix(**f) for f in fixes]

    # Evaluation
    evaluator = EvaluatorEngine()
    metrics = evaluator.evaluate(
        fixes_models,
        root_causes_models,
        bottlenecks_models,
        relevant_tokens,
        total_tokens
    )
    if isinstance(metrics, dict):
        metrics_dict = metrics
    elif isinstance(metrics, EvaluationMetrics):
        metrics_dict = metrics.dict()
    else:
        metrics_dict = dict(metrics)

    # Report (convert models to dicts for output)
    report = {
        "root_causes": [rc.dict() for rc in root_causes_models],
        "bottlenecks": [bn.dict() for bn in bottlenecks_models],
        "context_used": [
            {
                "file": k,
                "tokens": getattr(v, 'token_count', v['tokens'] if isinstance(v, dict) and 'tokens' in v else 0),
                "depth": getattr(v, 'depth', v['depth'] if isinstance(v, dict) and 'depth' in v else 0),
            }
            for k, v in dependency_context.items()
        ],
        "fixes": [f.dict() for f in fixes_models],
        "metrics": metrics_dict,
        "llm_requested": use_bedrock,
        "bedrock_available": BEDROCK_AVAILABLE,
        "final_score": metrics_dict.get("final_score", 0),
    }
    return report

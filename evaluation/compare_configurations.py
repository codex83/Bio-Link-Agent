"""
Configuration Comparison Script

Compares different system configurations (embedding models, eligibility parser settings, etc.)
on the labeled evaluation dataset to identify optimal settings.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.semantic_matcher import SemanticMatcher
from evaluation.metrics import calculate_metrics, EvaluationMetrics
from loguru import logger
import config


def load_labeled_dataset() -> dict:
    """Load the labeled evaluation dataset."""
    dataset_path = Path(__file__).parent / "labeled_dataset.json"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Labeled dataset not found: {dataset_path}")
    
    with open(dataset_path, 'r') as f:
        return json.load(f)


def extract_ground_truth_nct_ids(case: dict) -> set:
    """Extract ground truth NCT IDs from a labeled case."""
    ground_truth = set()
    for trial in case.get("ground_truth_trials", []):
        nct_id = trial.get("nct_id", "")
        if nct_id and nct_id != "REQUIRED":
            ground_truth.add(nct_id)
    return ground_truth


def get_model_identifier(model_name: str) -> str:
    """Get a short identifier for the model name to use in collection names."""
    if "biobert" in model_name.lower():
        return "biobert"
    elif "pubmedbert" in model_name.lower() or "biomednlp" in model_name.lower():
        return "pubmedbert"
    elif "minilm" in model_name.lower():
        return "minilm"
    else:
        # Use a hash of the model name
        import hashlib
        return hashlib.md5(model_name.encode()).hexdigest()[:8]


def evaluate_configuration(
    embedding_model: str,
    dataset: dict,
    top_k: int = 10,
    reindex: bool = True
) -> Dict:
    """
    Evaluate a specific configuration.
    
    Args:
        embedding_model: Embedding model name to use
        dataset: Labeled dataset
        top_k: Number of top matches to retrieve
        reindex: Whether to re-index trials for this model (required for different embedding dimensions)
    
    Returns:
        Evaluation results dictionary
    """
    logger.info(f"Evaluating configuration: {embedding_model}")
    
    # Initialize matcher with specific model
    matcher = SemanticMatcher(embedding_model=embedding_model)
    
    # Get model identifier for collection naming
    model_id = get_model_identifier(embedding_model)
    
    # Get unique conditions from dataset
    conditions = set(case["condition"] for case in dataset["evaluation_cases"])
    
    # Re-index trials for each condition with model-specific collection names
    if reindex:
        logger.info(f"Re-indexing trials for model: {embedding_model}")
        for condition in conditions:
            collection_name = f"{condition.lower().replace(' ', '_')}_{model_id}"
            logger.info(f"Indexing trials for condition: {condition} -> collection: {collection_name}")
            matcher.index_trials_for_condition(
                condition=condition,
                max_trials=100,
                collection_name=collection_name
            )
    
    all_predictions = []
    all_ground_truth = []
    all_scores = []
    
    for case in dataset["evaluation_cases"]:
        condition = case["condition"]
        # Use model-specific collection name
        collection_name = f"{condition.lower().replace(' ', '_')}_{model_id}"
        
        ground_truth = extract_ground_truth_nct_ids(case)
        if not ground_truth:
            continue
        
        try:
            matches = matcher.match_patient_to_trials(
                patient_description=case["patient_description"],
                collection_name=collection_name,
                patient_conditions=case.get("patient_conditions"),
                patient_age=case.get("patient_age"),
                patient_sex=case.get("patient_sex"),
                top_k=top_k
            )
            
            predicted_nct_ids = [m["nct_id"] for m in matches]
            predicted_scores = [m["score"] for m in matches]
            
            all_predictions.append(predicted_nct_ids)
            all_ground_truth.append(ground_truth)
            all_scores.append(predicted_scores)
            
        except Exception as e:
            logger.error(f"Error in case {case['patient_id']}: {e}")
            all_predictions.append([])
            all_ground_truth.append(ground_truth)
            all_scores.append([])
    
    metrics = calculate_metrics(all_predictions, all_ground_truth, all_scores)
    
    return {
        "embedding_model": embedding_model,
        "metrics": metrics.to_dict()
    }


def compare_configurations(
    models_to_test: List[str],
    dataset: dict,
    top_k: int = 10,
    reindex: bool = True
) -> Dict:
    """
    Compare multiple configurations.
    
    Args:
        models_to_test: List of embedding model names to compare
        dataset: Labeled dataset
        top_k: Number of top matches to retrieve
        reindex: Whether to re-index trials for each model (required for different embedding dimensions)
    
    Returns:
        Comparison results dictionary
    """
    results = {}
    
    for model in models_to_test:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing model: {model}")
        logger.info(f"{'='*60}")
        
        try:
            result = evaluate_configuration(model, dataset, top_k, reindex=reindex)
            results[model] = result
        except Exception as e:
            logger.error(f"Failed to evaluate {model}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            results[model] = {"error": str(e)}
    
    return results


def generate_comparison_report(results: Dict, output_path: Path):
    """Generate a comparison report."""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("CONFIGURATION COMPARISON REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"Generated: {datetime.now().isoformat()}")
    report_lines.append("")
    
    # Extract metrics for each configuration
    config_metrics = {}
    for model, result in results.items():
        if "error" in result:
            report_lines.append(f"Configuration: {model}")
            report_lines.append(f"  ERROR: {result['error']}")
            report_lines.append("")
            continue
        
        config_metrics[model] = EvaluationMetrics(**result["metrics"])
    
    if not config_metrics:
        report_lines.append("No valid configurations to compare.")
        return "\n".join(report_lines)
    
    # Compare key metrics
    report_lines.append("KEY METRICS COMPARISON")
    report_lines.append("-" * 80)
    report_lines.append("")
    
    # Precision@5
    report_lines.append("Precision@5:")
    for model, metrics in sorted(config_metrics.items(), key=lambda x: x[1].precision_at_5, reverse=True):
        report_lines.append(f"  {model:40s} {metrics.precision_at_5:.4f}")
    report_lines.append("")
    
    # Recall@5
    report_lines.append("Recall@5:")
    for model, metrics in sorted(config_metrics.items(), key=lambda x: x[1].recall_at_5, reverse=True):
        report_lines.append(f"  {model:40s} {metrics.recall_at_5:.4f}")
    report_lines.append("")
    
    # F1@5
    report_lines.append("F1@5:")
    for model, metrics in sorted(config_metrics.items(), key=lambda x: x[1].f1_at_5, reverse=True):
        report_lines.append(f"  {model:40s} {metrics.f1_at_5:.4f}")
    report_lines.append("")
    
    # MRR
    report_lines.append("Mean Reciprocal Rank (MRR):")
    for model, metrics in sorted(config_metrics.items(), key=lambda x: x[1].mean_reciprocal_rank, reverse=True):
        report_lines.append(f"  {model:40s} {metrics.mean_reciprocal_rank:.4f}")
    report_lines.append("")
    
    # Detailed metrics for each configuration
    report_lines.append("=" * 80)
    report_lines.append("DETAILED METRICS BY CONFIGURATION")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    for model, metrics in config_metrics.items():
        report_lines.append(f"Configuration: {model}")
        report_lines.append("-" * 80)
        report_lines.append(f"  Precision@1:  {metrics.precision_at_1:.4f}")
        report_lines.append(f"  Precision@3:  {metrics.precision_at_3:.4f}")
        report_lines.append(f"  Precision@5:  {metrics.precision_at_5:.4f}")
        report_lines.append(f"  Precision@10: {metrics.precision_at_10:.4f}")
        report_lines.append("")
        report_lines.append(f"  Recall@1:  {metrics.recall_at_1:.4f}")
        report_lines.append(f"  Recall@3:  {metrics.recall_at_3:.4f}")
        report_lines.append(f"  Recall@5:  {metrics.recall_at_5:.4f}")
        report_lines.append(f"  Recall@10: {metrics.recall_at_10:.4f}")
        report_lines.append("")
        report_lines.append(f"  F1@1:  {metrics.f1_at_1:.4f}")
        report_lines.append(f"  F1@3:  {metrics.f1_at_3:.4f}")
        report_lines.append(f"  F1@5:  {metrics.f1_at_5:.4f}")
        report_lines.append(f"  F1@10: {metrics.f1_at_10:.4f}")
        report_lines.append("")
        report_lines.append(f"  MRR: {metrics.mean_reciprocal_rank:.4f}")
        report_lines.append("")
        report_lines.append(f"  Avg Score (Correct):   {metrics.avg_score_correct:.4f}")
        report_lines.append(f"  Avg Score (Incorrect): {metrics.avg_score_incorrect:.4f}")
        report_lines.append(f"  Score Difference:      {metrics.score_difference:.4f}")
        report_lines.append("")
        report_lines.append(f"  Cases with Matches: {metrics.num_cases_with_matches}/{metrics.num_cases}")
        report_lines.append(f"  Cases with Correct: {metrics.num_cases_with_correct_matches}/{metrics.num_cases}")
        report_lines.append("")
    
    report = "\n".join(report_lines)
    
    with open(output_path, 'w') as f:
        f.write(report)
    
    print(report)
    return report


def main():
    """Main comparison function."""
    logger.info("Starting configuration comparison...")
    
    # Load dataset
    dataset = load_labeled_dataset()
    
    # Check for ground truth labels
    cases_with_labels = sum(
        1 for case in dataset["evaluation_cases"]
        if extract_ground_truth_nct_ids(case)
    )
    
    if cases_with_labels == 0:
        logger.error("No ground truth labels found!")
        logger.info("Please run evaluation/generate_ground_truth.py first.")
        return
    
    logger.info(f"Found {cases_with_labels} cases with ground truth labels")
    
    # Compare BioBERT vs PubMedBERT (both are biomedical domain models)
    models_to_test = [
        "dmis-lab/biobert-base-cased-v1.1",  # Current default
        "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"  # PubMedBERT
    ]
    
    logger.info("\nComparing embedding models:")
    for model in models_to_test:
        logger.info(f"  - {model}")
    logger.info("\nThis will re-index trials for each model, which may take several minutes...")
    
    # Compare configurations (reindex=True to ensure each model has its own collections)
    results = compare_configurations(models_to_test, dataset, top_k=10, reindex=True)
    
    # Generate comparison report
    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"pubmedbert_vs_biobert_comparison_{timestamp}.txt"
    
    generate_comparison_report(results, output_path)
    
    # Also save JSON results
    json_path = output_dir / f"pubmedbert_vs_biobert_results_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nComparison complete!")
    logger.info(f"Report: {output_path}")
    logger.info(f"JSON results: {json_path}")


if __name__ == "__main__":
    main()


"""
Evaluation Runner for Bio-Link Agent

Runs the semantic matcher on labeled patient cases and calculates evaluation metrics.
Compares predictions against ground truth labels to measure system performance.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Set
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.semantic_matcher import SemanticMatcher
from evaluation.metrics import calculate_metrics, format_metrics_report, EvaluationMetrics
from loguru import logger
import config


def load_labeled_dataset() -> dict:
    """Load the labeled evaluation dataset."""
    dataset_path = Path(__file__).parent / "labeled_dataset.json"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Labeled dataset not found: {dataset_path}")
    
    with open(dataset_path, 'r') as f:
        return json.load(f)


def extract_ground_truth_nct_ids(case: dict) -> Set[str]:
    """Extract ground truth NCT IDs from a labeled case."""
    ground_truth = set()
    for trial in case.get("ground_truth_trials", []):
        nct_id = trial.get("nct_id", "")
        if nct_id and nct_id != "REQUIRED":
            ground_truth.add(nct_id)
    return ground_truth


def run_evaluation(
    matcher: SemanticMatcher,
    dataset: dict,
    top_k: int = 10
) -> Dict:
    """
    Run evaluation on all labeled cases.
    
    Args:
        matcher: Initialized SemanticMatcher instance
        dataset: Labeled dataset dictionary
        top_k: Number of top matches to retrieve per case
    
    Returns:
        Dictionary containing evaluation results
    """
    all_predictions = []
    all_ground_truth = []
    all_scores = []
    case_details = []
    
    logger.info(f"Running evaluation on {len(dataset['evaluation_cases'])} test cases...")
    
    for i, case in enumerate(dataset["evaluation_cases"], 1):
        patient_id = case["patient_id"]
        condition = case["condition"]
        collection_name = condition  # Collection names match condition names (lung_cancer, glioblastoma, type_2_diabetes)
        
        logger.info(f"Processing case {i}/{len(dataset['evaluation_cases'])}: {patient_id}")
        
        # Extract ground truth
        ground_truth = extract_ground_truth_nct_ids(case)
        
        if not ground_truth:
            logger.warning(f"No ground truth labels for {patient_id}, skipping...")
            continue
        
        # Run semantic matcher
        try:
            matches = matcher.match_patient_to_trials(
                patient_description=case["patient_description"],
                collection_name=collection_name,
                patient_conditions=case.get("patient_conditions"),
                patient_age=case.get("patient_age"),
                patient_sex=case.get("patient_sex"),
                top_k=top_k
            )
            
            # Extract predicted NCT IDs and scores
            predicted_nct_ids = [m["nct_id"] for m in matches]
            predicted_scores = [m["score"] for m in matches]
            
            # Store results
            all_predictions.append(predicted_nct_ids)
            all_ground_truth.append(ground_truth)
            all_scores.append(predicted_scores)
            
            # Calculate case-level metrics
            correct_in_top_k = sum(1 for nct_id in predicted_nct_ids if nct_id in ground_truth)
            first_correct_rank = None
            for rank, nct_id in enumerate(predicted_nct_ids, start=1):
                if nct_id in ground_truth:
                    first_correct_rank = rank
                    break
            
            case_details.append({
                "patient_id": patient_id,
                "condition": condition,
                "num_ground_truth": len(ground_truth),
                "num_predictions": len(predicted_nct_ids),
                "correct_in_top_k": correct_in_top_k,
                "first_correct_rank": first_correct_rank,
                "top_score": predicted_scores[0] if predicted_scores else 0.0,
                "ground_truth_nct_ids": list(ground_truth),
                "predicted_nct_ids": predicted_nct_ids[:5]  # Store top 5 for reference
            })
            
            logger.info(f"  Found {len(predicted_nct_ids)} matches, {correct_in_top_k} correct in top-{top_k}")
            
        except Exception as e:
            logger.error(f"Error processing case {patient_id}: {e}")
            # Add empty results for failed cases
            all_predictions.append([])
            all_ground_truth.append(ground_truth)
            all_scores.append([])
            case_details.append({
                "patient_id": patient_id,
                "condition": condition,
                "error": str(e)
            })
    
    # Calculate aggregate metrics
    logger.info("Calculating evaluation metrics...")
    metrics = calculate_metrics(all_predictions, all_ground_truth, all_scores)
    
    return {
        "metrics": metrics.to_dict(),
        "case_details": case_details,
        "evaluation_config": {
            "embedding_model": config.EMBEDDING_MODEL,
            "top_k": top_k,
            "num_cases": len(dataset["evaluation_cases"]),
            "timestamp": datetime.now().isoformat()
        }
    }


def generate_evaluation_report(results: Dict, output_path: Path):
    """Generate a detailed evaluation report."""
    metrics = EvaluationMetrics(**results["metrics"])
    
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("BIO-LINK AGENT EVALUATION REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # Configuration
    config_info = results["evaluation_config"]
    report_lines.append("Evaluation Configuration:")
    report_lines.append(f"  Embedding Model: {config_info['embedding_model']}")
    report_lines.append(f"    (BioBERT is specifically designed for biomedical text)")
    report_lines.append(f"  Top-K: {config_info['top_k']}")
    report_lines.append(f"  Test Cases: {config_info['num_cases']}")
    report_lines.append(f"  Timestamp: {config_info['timestamp']}")
    report_lines.append("")
    report_lines.append("Note: Ground truth labels are automatically generated using")
    report_lines.append("      the system's eligibility parser and semantic matching.")
    report_lines.append("")
    
    # Aggregate metrics
    report_lines.append(format_metrics_report(metrics))
    report_lines.append("")
    
    # Per-case details
    report_lines.append("=" * 80)
    report_lines.append("PER-CASE DETAILS")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    for case in results["case_details"]:
        if "error" in case:
            report_lines.append(f"Case: {case['patient_id']} ({case['condition']})")
            report_lines.append(f"  ERROR: {case['error']}")
            report_lines.append("")
            continue
        
        report_lines.append(f"Case: {case['patient_id']} ({case['condition']})")
        report_lines.append(f"  Ground Truth Trials: {case['num_ground_truth']}")
        report_lines.append(f"  Predicted Matches: {case['num_predictions']}")
        report_lines.append(f"  Correct in Top-{config_info['top_k']}: {case['correct_in_top_k']}")
        
        if case['first_correct_rank']:
            report_lines.append(f"  First Correct Match at Rank: {case['first_correct_rank']}")
        else:
            report_lines.append(f"  First Correct Match at Rank: Not found")
        
        report_lines.append(f"  Top Match Score: {case['top_score']:.4f}")
        report_lines.append(f"  Ground Truth NCT IDs: {', '.join(case['ground_truth_nct_ids'])}")
        report_lines.append(f"  Top 5 Predicted: {', '.join(case['predicted_nct_ids'])}")
        report_lines.append("")
    
    report = "\n".join(report_lines)
    
    # Save to file
    with open(output_path, 'w') as f:
        f.write(report)
    
    # Also print to console
    print(report)
    
    return report


def main():
    """Main evaluation function."""
    logger.info("Starting evaluation...")
    
    # Load labeled dataset
    logger.info("Loading labeled dataset...")
    dataset = load_labeled_dataset()
    
    # Check if dataset has ground truth labels
    cases_with_labels = sum(
        1 for case in dataset["evaluation_cases"]
        if extract_ground_truth_nct_ids(case)
    )
    
    if cases_with_labels == 0:
        logger.error("No ground truth labels found in dataset!")
        logger.info("Please run evaluation/populate_ground_truth.py first to label the dataset.")
        return
    
    logger.info(f"Found {cases_with_labels} cases with ground truth labels")
    
    # Initialize semantic matcher
    logger.info(f"Initializing semantic matcher with model: {config.EMBEDDING_MODEL}")
    matcher = SemanticMatcher(embedding_model=config.EMBEDDING_MODEL)
    
    # Run evaluation
    results = run_evaluation(matcher, dataset, top_k=10)
    
    # Generate report
    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"evaluation_report_{timestamp}.txt"
    
    logger.info(f"Generating evaluation report...")
    generate_evaluation_report(results, output_path)
    
    # Also save JSON results
    json_path = output_dir / f"evaluation_results_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nEvaluation complete!")
    logger.info(f"Report saved to: {output_path}")
    logger.info(f"JSON results saved to: {json_path}")


if __name__ == "__main__":
    main()


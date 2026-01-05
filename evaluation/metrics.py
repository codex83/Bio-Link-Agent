"""
Evaluation Metrics for Bio-Link Agent

Provides metrics for evaluating patient-trial matching performance:
- Precision@K: Fraction of top-K results that are correct
- Recall@K: Fraction of correct trials found in top-K
- Mean Reciprocal Rank (MRR): Average of 1/rank for first correct match
- F1@K: Harmonic mean of Precision@K and Recall@K
- Average Match Score: Mean similarity score for correct vs incorrect matches
"""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import numpy as np
from loguru import logger


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics."""
    precision_at_1: float = 0.0
    precision_at_3: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    
    recall_at_1: float = 0.0
    recall_at_3: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    
    f1_at_1: float = 0.0
    f1_at_3: float = 0.0
    f1_at_5: float = 0.0
    f1_at_10: float = 0.0
    
    mean_reciprocal_rank: float = 0.0
    
    avg_score_correct: float = 0.0
    avg_score_incorrect: float = 0.0
    score_difference: float = 0.0
    
    num_cases: int = 0
    num_cases_with_matches: int = 0
    num_cases_with_correct_matches: int = 0
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "precision_at_1": self.precision_at_1,
            "precision_at_3": self.precision_at_3,
            "precision_at_5": self.precision_at_5,
            "precision_at_10": self.precision_at_10,
            "recall_at_1": self.recall_at_1,
            "recall_at_3": self.recall_at_3,
            "recall_at_5": self.recall_at_5,
            "recall_at_10": self.recall_at_10,
            "f1_at_1": self.f1_at_1,
            "f1_at_3": self.f1_at_3,
            "f1_at_5": self.f1_at_5,
            "f1_at_10": self.f1_at_10,
            "mean_reciprocal_rank": self.mean_reciprocal_rank,
            "avg_score_correct": self.avg_score_correct,
            "avg_score_incorrect": self.avg_score_incorrect,
            "score_difference": self.score_difference,
            "num_cases": self.num_cases,
            "num_cases_with_matches": self.num_cases_with_matches,
            "num_cases_with_correct_matches": self.num_cases_with_correct_matches
        }


def precision_at_k(predicted: List[str], ground_truth: Set[str], k: int) -> float:
    """
    Calculate Precision@K.
    
    Args:
        predicted: List of predicted NCT IDs (ordered by relevance)
        ground_truth: Set of correct NCT IDs
        k: Number of top results to consider
    
    Returns:
        Precision@K score (0.0 to 1.0)
    """
    if not predicted or not ground_truth:
        return 0.0
    
    top_k = predicted[:k]
    if not top_k:
        return 0.0
    
    correct = sum(1 for nct_id in top_k if nct_id in ground_truth)
    return correct / len(top_k)


def recall_at_k(predicted: List[str], ground_truth: Set[str], k: int) -> float:
    """
    Calculate Recall@K.
    
    Args:
        predicted: List of predicted NCT IDs (ordered by relevance)
        ground_truth: Set of correct NCT IDs
        k: Number of top results to consider
    
    Returns:
        Recall@K score (0.0 to 1.0)
    """
    if not ground_truth:
        return 0.0
    
    if not predicted:
        return 0.0
    
    top_k = predicted[:k]
    correct = sum(1 for nct_id in top_k if nct_id in ground_truth)
    return correct / len(ground_truth)


def f1_at_k(predicted: List[str], ground_truth: Set[str], k: int) -> float:
    """
    Calculate F1@K (harmonic mean of Precision@K and Recall@K).
    
    Args:
        predicted: List of predicted NCT IDs (ordered by relevance)
        ground_truth: Set of correct NCT IDs
        k: Number of top results to consider
    
    Returns:
        F1@K score (0.0 to 1.0)
    """
    prec = precision_at_k(predicted, ground_truth, k)
    rec = recall_at_k(predicted, ground_truth, k)
    
    if prec + rec == 0:
        return 0.0
    
    return 2 * (prec * rec) / (prec + rec)


def mean_reciprocal_rank(predicted: List[str], ground_truth: Set[str]) -> float:
    """
    Calculate Mean Reciprocal Rank (MRR).
    
    MRR = 1 / rank of first correct match, or 0 if no correct match.
    
    Args:
        predicted: List of predicted NCT IDs (ordered by relevance)
        ground_truth: Set of correct NCT IDs
    
    Returns:
        Reciprocal rank (0.0 to 1.0)
    """
    if not predicted or not ground_truth:
        return 0.0
    
    for rank, nct_id in enumerate(predicted, start=1):
        if nct_id in ground_truth:
            return 1.0 / rank
    
    return 0.0


def calculate_metrics(
    all_predictions: List[List[str]],
    all_ground_truth: List[Set[str]],
    all_scores: Optional[List[List[float]]] = None
) -> EvaluationMetrics:
    """
    Calculate comprehensive evaluation metrics across all test cases.
    
    Args:
        all_predictions: List of predicted NCT ID lists (one per test case)
        all_ground_truth: List of ground truth NCT ID sets (one per test case)
        all_scores: Optional list of score lists (one per test case)
    
    Returns:
        EvaluationMetrics object with aggregated metrics
    """
    if len(all_predictions) != len(all_ground_truth):
        raise ValueError("Predictions and ground truth must have same length")
    
    if all_scores and len(all_scores) != len(all_predictions):
        raise ValueError("Scores must have same length as predictions")
    
    metrics = EvaluationMetrics()
    metrics.num_cases = len(all_predictions)
    
    # Calculate metrics for each K value
    k_values = [1, 3, 5, 10]
    precisions = {k: [] for k in k_values}
    recalls = {k: [] for k in k_values}
    f1_scores = {k: [] for k in k_values}
    reciprocal_ranks = []
    
    # Track scores for correct vs incorrect matches
    correct_scores = []
    incorrect_scores = []
    
    for i, (predicted, ground_truth) in enumerate(zip(all_predictions, all_ground_truth)):
        if not predicted:
            # No matches found
            for k in k_values:
                precisions[k].append(0.0)
                recalls[k].append(0.0)
                f1_scores[k].append(0.0)
            reciprocal_ranks.append(0.0)
            continue
        
        metrics.num_cases_with_matches += 1
        
        # Calculate metrics at different K values
        for k in k_values:
            prec = precision_at_k(predicted, ground_truth, k)
            rec = recall_at_k(predicted, ground_truth, k)
            f1 = f1_at_k(predicted, ground_truth, k)
            
            precisions[k].append(prec)
            recalls[k].append(rec)
            f1_scores[k].append(f1)
        
        # Calculate MRR
        rr = mean_reciprocal_rank(predicted, ground_truth)
        reciprocal_ranks.append(rr)
        
        if rr > 0:
            metrics.num_cases_with_correct_matches += 1
        
        # Track scores if provided
        if all_scores and all_scores[i]:
            scores = all_scores[i]
            for j, nct_id in enumerate(predicted):
                if j < len(scores):
                    score = scores[j]
                    if nct_id in ground_truth:
                        correct_scores.append(score)
                    else:
                        incorrect_scores.append(score)
    
    # Aggregate metrics
    metrics.precision_at_1 = np.mean(precisions[1]) if precisions[1] else 0.0
    metrics.precision_at_3 = np.mean(precisions[3]) if precisions[3] else 0.0
    metrics.precision_at_5 = np.mean(precisions[5]) if precisions[5] else 0.0
    metrics.precision_at_10 = np.mean(precisions[10]) if precisions[10] else 0.0
    
    metrics.recall_at_1 = np.mean(recalls[1]) if recalls[1] else 0.0
    metrics.recall_at_3 = np.mean(recalls[3]) if recalls[3] else 0.0
    metrics.recall_at_5 = np.mean(recalls[5]) if recalls[5] else 0.0
    metrics.recall_at_10 = np.mean(recalls[10]) if recalls[10] else 0.0
    
    metrics.f1_at_1 = np.mean(f1_scores[1]) if f1_scores[1] else 0.0
    metrics.f1_at_3 = np.mean(f1_scores[3]) if f1_scores[3] else 0.0
    metrics.f1_at_5 = np.mean(f1_scores[5]) if f1_scores[5] else 0.0
    metrics.f1_at_10 = np.mean(f1_scores[10]) if f1_scores[10] else 0.0
    
    metrics.mean_reciprocal_rank = np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0
    
    # Calculate average scores
    if correct_scores:
        metrics.avg_score_correct = np.mean(correct_scores)
    if incorrect_scores:
        metrics.avg_score_incorrect = np.mean(incorrect_scores)
    if correct_scores and incorrect_scores:
        metrics.score_difference = metrics.avg_score_correct - metrics.avg_score_incorrect
    
    return metrics


def format_metrics_report(metrics: EvaluationMetrics) -> str:
    """
    Format metrics as a human-readable report.
    
    Args:
        metrics: EvaluationMetrics object
    
    Returns:
        Formatted report string
    """
    report = []
    report.append("=" * 80)
    report.append("EVALUATION METRICS REPORT")
    report.append("=" * 80)
    report.append("")
    
    report.append("Precision@K (Fraction of top-K results that are correct):")
    report.append(f"  Precision@1:  {metrics.precision_at_1:.4f}")
    report.append(f"  Precision@3:  {metrics.precision_at_3:.4f}")
    report.append(f"  Precision@5:  {metrics.precision_at_5:.4f}")
    report.append(f"  Precision@10: {metrics.precision_at_10:.4f}")
    report.append("")
    
    report.append("Recall@K (Fraction of correct trials found in top-K):")
    report.append(f"  Recall@1:  {metrics.recall_at_1:.4f}")
    report.append(f"  Recall@3:  {metrics.recall_at_3:.4f}")
    report.append(f"  Recall@5:  {metrics.recall_at_5:.4f}")
    report.append(f"  Recall@10: {metrics.recall_at_10:.4f}")
    report.append("")
    
    report.append("F1@K (Harmonic mean of Precision@K and Recall@K):")
    report.append(f"  F1@1:  {metrics.f1_at_1:.4f}")
    report.append(f"  F1@3:  {metrics.f1_at_3:.4f}")
    report.append(f"  F1@5:  {metrics.f1_at_5:.4f}")
    report.append(f"  F1@10: {metrics.f1_at_10:.4f}")
    report.append("")
    
    report.append("Mean Reciprocal Rank (MRR):")
    report.append(f"  MRR: {metrics.mean_reciprocal_rank:.4f}")
    report.append("")
    
    report.append("Match Score Analysis:")
    report.append(f"  Average score (correct matches):   {metrics.avg_score_correct:.4f}")
    report.append(f"  Average score (incorrect matches): {metrics.avg_score_incorrect:.4f}")
    report.append(f"  Score difference:                  {metrics.score_difference:.4f}")
    report.append("")
    
    report.append("Case Statistics:")
    report.append(f"  Total test cases:              {metrics.num_cases}")
    report.append(f"  Cases with matches:            {metrics.num_cases_with_matches}")
    report.append(f"  Cases with correct matches:    {metrics.num_cases_with_correct_matches}")
    report.append(f"  Cases with no matches:         {metrics.num_cases - metrics.num_cases_with_matches}")
    report.append("")
    
    report.append("=" * 80)
    
    return "\n".join(report)


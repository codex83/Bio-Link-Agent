"""
Automated Ground Truth Generation

This script automatically generates initial ground truth labels by:
1. Running the semantic matcher on each patient case
2. Using the eligibility parser to identify trials where the patient is actually eligible
3. Filtering for high-confidence matches (high semantic score + passes eligibility)
4. Saving the results as ground truth candidates for manual review

This provides a starting point that can be refined manually.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Set

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.semantic_matcher import SemanticMatcher
from loguru import logger
import config


def load_labeled_dataset() -> dict:
    """Load the labeled dataset template."""
    dataset_path = Path(__file__).parent / "labeled_dataset.json"
    with open(dataset_path, 'r') as f:
        return json.load(f)


def save_labeled_dataset(dataset: dict):
    """Save the labeled dataset."""
    dataset_path = Path(__file__).parent / "labeled_dataset.json"
    with open(dataset_path, 'w') as f:
        json.dump(dataset, f, indent=2)


def generate_ground_truth_for_case(
    matcher: SemanticMatcher,
    case: dict,
    collection_name: str,
    min_score_threshold: float = 0.8,
    max_candidates: int = 5
) -> List[Dict]:
    """
    Generate ground truth candidates for a patient case.
    
    Args:
        matcher: Initialized SemanticMatcher
        case: Patient case dictionary
        collection_name: ChromaDB collection name
        min_score_threshold: Minimum semantic similarity score
        max_candidates: Maximum number of candidates to return
    
    Returns:
        List of ground truth candidate dictionaries
    """
    logger.info(f"Generating ground truth for {case['patient_id']}...")
    
    # Run semantic matcher with more candidates
    matches = matcher.match_patient_to_trials(
        patient_description=case["patient_description"],
        collection_name=collection_name,
        patient_conditions=case.get("patient_conditions"),
        patient_age=case.get("patient_age"),
        patient_sex=case.get("patient_sex"),
        top_k=20  # Get more candidates
    )
    
    if not matches:
        logger.warning(f"No matches found for {case['patient_id']}")
        return []
    
    # Filter for high-confidence matches
    # These are trials that:
    # 1. Passed eligibility filtering (already filtered by match_patient_to_trials)
    # 2. Have high semantic similarity scores
    # 3. Match the patient's condition
    
    candidates = []
    for match in matches:
        score = match.get("score", 0.0)
        
        # Only consider high-scoring matches
        if score < min_score_threshold:
            continue
        
        # Check if trial conditions align with patient conditions
        metadata = match.get("metadata", {})
        trial_conditions = metadata.get("conditions", "").lower()
        patient_conditions = [c.lower() for c in case.get("patient_conditions", [])]
        
        condition_match = False
        for pc in patient_conditions:
            if pc in trial_conditions or any(pc in tc for tc in trial_conditions.split(", ")):
                condition_match = True
                break
        
        if condition_match:
            candidates.append({
                "nct_id": match["nct_id"],
                "match_type": "auto_generated",
                "reason": f"High semantic score ({score:.3f}) and patient passes eligibility criteria",
                "score": score,
                "title": metadata.get("title", "")[:100]
            })
        
        if len(candidates) >= max_candidates:
            break
    
    logger.info(f"Generated {len(candidates)} ground truth candidates for {case['patient_id']}")
    return candidates


def main():
    """Main function to generate ground truth labels."""
    logger.info("Starting automated ground truth generation...")
    
    # Load dataset
    dataset = load_labeled_dataset()
    
    # Initialize matcher
    logger.info(f"Initializing semantic matcher with model: {config.EMBEDDING_MODEL}")
    matcher = SemanticMatcher(embedding_model=config.EMBEDDING_MODEL)
    
    # Group cases by condition
    cases_by_condition = {}
    for case in dataset["evaluation_cases"]:
        condition = case["condition"]
        if condition not in cases_by_condition:
            cases_by_condition[condition] = []
        cases_by_condition[condition].append(case)
    
    # Process each condition
    total_generated = 0
    for condition, cases in cases_by_condition.items():
        collection_name = condition
        
        logger.info(f"\nProcessing condition: {condition}")
        
        # Check if collection exists
        try:
            info = matcher.get_collection_info(collection_name)
            logger.info(f"Trials indexed: {info.get('count', 0)}")
        except Exception as e:
            logger.error(f"Collection {collection_name} not found: {e}")
            logger.info(f"Skipping condition {condition}")
            continue
        
        # Process each case
        for case in cases:
            try:
                candidates = generate_ground_truth_for_case(
                    matcher,
                    case,
                    collection_name,
                    min_score_threshold=0.8,
                    max_candidates=3  # Generate top 3 candidates
                )
                
                if candidates:
                    # Update the case with generated ground truth
                    case["ground_truth_trials"] = [
                        {
                            "nct_id": c["nct_id"],
                            "match_type": c["match_type"],
                            "reason": c["reason"]
                        }
                        for c in candidates
                    ]
                    case["_auto_generated"] = True
                    case["_generation_metadata"] = {
                        "num_candidates": len(candidates),
                        "scores": [c["score"] for c in candidates]
                    }
                    total_generated += len(candidates)
                    logger.info(f"✓ Generated {len(candidates)} candidates for {case['patient_id']}")
                else:
                    logger.warning(f"⊘ No candidates generated for {case['patient_id']}")
                    # Keep the original "REQUIRED" placeholder
                
            except Exception as e:
                logger.error(f"Error processing case {case['patient_id']}: {e}")
                continue
    
    # Save updated dataset
    save_labeled_dataset(dataset)
    
    logger.info("\n" + "=" * 80)
    logger.info(f"Ground truth generation complete!")
    logger.info(f"Generated {total_generated} ground truth candidates across {len(dataset['evaluation_cases'])} cases")
    logger.info("=" * 80)
    logger.info("\nNOTE: These are automatically generated candidates based on:")
    logger.info("  - High semantic similarity scores (>= 0.8)")
    logger.info("  - Eligibility criteria validation")
    logger.info("  - Condition matching")
    logger.info("\nPlease review and refine these labels using populate_ground_truth.py")
    logger.info(f"Dataset saved to: {Path(__file__).parent / 'labeled_dataset.json'}")


if __name__ == "__main__":
    main()


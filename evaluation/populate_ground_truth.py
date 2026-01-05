"""
Helper script to populate labeled_dataset.json with actual NCT IDs.

This script helps identify ground truth trial matches by:
1. Running the semantic matcher on each patient case
2. Displaying top matches for manual review
3. Allowing user to select which trials are correct matches
4. Saving the labeled dataset with actual NCT IDs
"""

import sys
import os
import json
from pathlib import Path

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


def display_trial_match(match: dict, index: int):
    """Display a trial match for review."""
    metadata = match.get("metadata", {})
    print(f"\n  [{index}] {match.get('nct_id', 'N/A')}")
    print(f"      Title: {metadata.get('title', 'N/A')[:80]}...")
    print(f"      Conditions: {metadata.get('conditions', 'N/A')}")
    print(f"      Age: {metadata.get('min_age', 'N/A')}-{metadata.get('max_age', 'N/A')}, Sex: {metadata.get('sex', 'ALL')}")
    print(f"      Score: {match.get('score', 0.0):.4f}")
    print(f"      Reasoning: {match.get('reasoning', 'N/A')[:100]}...")


def review_patient_case(matcher: SemanticMatcher, case: dict, collection_name: str):
    """Review matches for a patient case and get ground truth labels."""
    print("\n" + "=" * 80)
    print(f"Patient: {case['patient_id']}")
    print(f"Description: {case['patient_description'][:150]}...")
    print("=" * 80)
    
    # Run semantic matcher
    matches = matcher.match_patient_to_trials(
        patient_description=case["patient_description"],
        collection_name=collection_name,
        patient_conditions=case.get("patient_conditions"),
        patient_age=case.get("patient_age"),
        patient_sex=case.get("patient_sex"),
        top_k=20  # Get more matches for review
    )
    
    if not matches:
        print("\nNo matches found for this patient.")
        return []
    
    print(f"\nFound {len(matches)} matches. Review top matches:")
    print("\nTop 10 matches:")
    for i, match in enumerate(matches[:10], 1):
        display_trial_match(match, i)
    
    print("\n" + "-" * 80)
    print("Select which trials are CORRECT matches (ground truth):")
    print("Enter NCT IDs separated by commas, or 'skip' to skip this case")
    print("Example: NCT12345678,NCT87654321")
    
    user_input = input("\nYour selection: ").strip()
    
    if user_input.lower() == 'skip':
        return []
    
    selected_nct_ids = [nct.strip() for nct in user_input.split(',') if nct.strip()]
    
    # Validate that selected NCT IDs are in the matches
    available_nct_ids = {m['nct_id'] for m in matches}
    valid_nct_ids = [nct for nct in selected_nct_ids if nct in available_nct_ids]
    
    if valid_nct_ids != selected_nct_ids:
        invalid = set(selected_nct_ids) - set(valid_nct_ids)
        print(f"Warning: Some NCT IDs not found in matches: {invalid}")
    
    return valid_nct_ids


def main():
    """Main function to populate ground truth labels."""
    logger.info("Loading labeled dataset template...")
    dataset = load_labeled_dataset()
    
    logger.info("Initializing semantic matcher...")
    matcher = SemanticMatcher(embedding_model=config.EMBEDDING_MODEL)
    
    print("\n" + "=" * 80)
    print("GROUND TRUTH LABELING TOOL")
    print("=" * 80)
    print("\nThis tool will help you identify correct trial matches for each patient case.")
    print("For each patient, review the top matches and select which ones are correct.")
    print("\nPress Ctrl+C at any time to save progress and exit.")
    print("=" * 80)
    
    # Group cases by condition
    cases_by_condition = {}
    for case in dataset["evaluation_cases"]:
        condition = case["condition"]
        if condition not in cases_by_condition:
            cases_by_condition[condition] = []
        cases_by_condition[condition].append(case)
    
    # Process each condition
    for condition, cases in cases_by_condition.items():
        collection_name = condition  # Collection names match condition names (lung_cancer, glioblastoma, type_2_diabetes)
        
        print(f"\n\nProcessing condition: {condition}")
        print(f"Collection: {collection_name}")
        print(f"Number of cases: {len(cases)}")
        
        # Check if collection exists
        try:
            info = matcher.get_collection_info(collection_name)
            print(f"Trials indexed: {info.get('count', 0)}")
        except Exception as e:
            logger.error(f"Collection {collection_name} not found or error: {e}")
            print(f"Skipping condition {condition} - collection not found")
            continue
        
        # Process each case
        for case in cases:
            try:
                ground_truth_nct_ids = review_patient_case(matcher, case, collection_name)
                
                # Update the case with ground truth
                if ground_truth_nct_ids:
                    case["ground_truth_trials"] = [
                        {
                            "nct_id": nct_id,
                            "match_type": "exact",
                            "reason": "Manually labeled as correct match"
                        }
                        for nct_id in ground_truth_nct_ids
                    ]
                    print(f"\n✓ Labeled {len(ground_truth_nct_ids)} correct matches for {case['patient_id']}")
                else:
                    print(f"\n⊘ Skipped labeling for {case['patient_id']}")
                
                # Save progress after each case
                save_labeled_dataset(dataset)
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Saving progress...")
                save_labeled_dataset(dataset)
                print("Progress saved. Exiting.")
                return
            except Exception as e:
                logger.error(f"Error processing case {case['patient_id']}: {e}")
                continue
    
    print("\n" + "=" * 80)
    print("Labeling complete!")
    print("=" * 80)
    save_labeled_dataset(dataset)
    print(f"\nLabeled dataset saved to: {Path(__file__).parent / 'labeled_dataset.json'}")


if __name__ == "__main__":
    main()


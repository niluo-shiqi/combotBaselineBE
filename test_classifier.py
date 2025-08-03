#!/usr/bin/env python3

import os
import sys

# Add the current directory to Python path
sys.path.append('.')

# Set environment variables
os.environ["TRANSFORMERS_CACHE"] = "./cache"
os.environ["USE_TF"] = "0"

def test_classifier():
    """Test the Hugging Face classifier to see what it returns"""
    try:
        from transformers import pipeline
        print("Loading classifier...")
        classifier = pipeline("text-classification", model="jpsteinhafel/complaints_classifier")
        print("Classifier loaded successfully!")
        
        # Test cases
        test_cases = [
            "My leggings ripped after only 2 wears",
            "The employee was really rude to me",
            "My package never arrived",
            "My leggings ripped AND the employee was rude about it",
            "The delivery was late and the employee was unhelpful"
        ]
        
        for i, test_input in enumerate(test_cases, 1):
            print(f"\n=== Test Case {i} ===")
            print(f"Input: {test_input}")
            
            # Get the result
            result = classifier(test_input)
            print(f"Result: {result}")
            print(f"Type: {type(result)}")
            print(f"Length: {len(result)}")
            
            # Try to get all predictions
            try:
                # Try to get all scores
                all_results = classifier(test_input, return_all_scores=True)
                print(f"All scores: {all_results}")
            except Exception as e:
                print(f"Could not get all scores: {e}")
            
            # Try to get top k predictions
            try:
                top_k_results = classifier(test_input, top_k=3)
                print(f"Top 3 predictions: {top_k_results}")
            except Exception as e:
                print(f"Could not get top k: {e}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_classifier() 
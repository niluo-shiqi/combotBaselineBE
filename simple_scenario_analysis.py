#!/usr/bin/env python3
"""
Simple Scenario Distribution Analysis
Analyzes how randomness and distribution of 8 scenarios is affected
when scaling from 15 to 30 users per session
"""

import random
import json
from collections import Counter
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SimpleScenarioAnalyzer:
    def __init__(self):
        # Define the 8 possible scenarios
        self.scenarios = [
            {"brand": "Nike", "problem_type": "A", "think_level": "Low", "feel_level": "Low"},
            {"brand": "Nike", "problem_type": "A", "think_level": "Low", "feel_level": "High"},
            {"brand": "Nike", "problem_type": "A", "think_level": "High", "feel_level": "Low"},
            {"brand": "Nike", "problem_type": "A", "think_level": "High", "feel_level": "High"},
            {"brand": "Lulu", "problem_type": "B", "think_level": "Low", "feel_level": "Low"},
            {"brand": "Lulu", "problem_type": "B", "think_level": "Low", "feel_level": "High"},
            {"brand": "Lulu", "problem_type": "B", "think_level": "High", "feel_level": "Low"},
            {"brand": "Lulu", "problem_type": "B", "think_level": "High", "feel_level": "High"}
        ]
        
        # Scenario labels for analysis
        self.scenario_labels = [
            "Nike-A-Low-Low",
            "Nike-A-Low-High", 
            "Nike-A-High-Low",
            "Nike-A-High-High",
            "Lulu-B-Low-Low",
            "Lulu-B-Low-High",
            "Lulu-B-High-Low", 
            "Lulu-B-High-High"
        ]

    def calculate_mean(self, numbers):
        """Calculate mean of a list of numbers"""
        return sum(numbers) / len(numbers) if numbers else 0

    def calculate_std(self, numbers):
        """Calculate standard deviation of a list of numbers"""
        if not numbers:
            return 0
        mean = self.calculate_mean(numbers)
        variance = sum((x - mean) ** 2 for x in numbers) / len(numbers)
        return variance ** 0.5

    def simulate_random_distribution(self, num_users, num_sessions=100):
        """Simulate random scenario distribution for given number of users"""
        all_distributions = []
        
        for session in range(num_sessions):
            # Simulate random selection for this session
            session_scenarios = []
            for user in range(num_users):
                scenario = random.choice(self.scenarios)
                scenario_index = self.scenarios.index(scenario)
                session_scenarios.append(scenario_index)
            
            # Count distribution for this session
            distribution = Counter(session_scenarios)
            all_distributions.append(dict(distribution))
        
        return all_distributions

    def analyze_distribution_quality(self, distributions, expected_per_scenario):
        """Analyze the quality of distribution"""
        results = {
            'sessions': len(distributions),
            'expected_per_scenario': expected_per_scenario,
            'scenario_analysis': {},
            'overall_stats': {}
        }
        
        # Analyze each scenario
        for scenario_idx in range(8):
            scenario_name = self.scenario_labels[scenario_idx]
            scenario_counts = [dist.get(scenario_idx, 0) for dist in distributions]
            
            mean_count = self.calculate_mean(scenario_counts)
            std_count = self.calculate_std(scenario_counts)
            min_count = min(scenario_counts) if scenario_counts else 0
            max_count = max(scenario_counts) if scenario_counts else 0
            
            # Calculate distribution quality metrics
            cv = (std_count / mean_count) if mean_count > 0 else 0  # Coefficient of variation
            coverage = sum(1 for count in scenario_counts if count > 0) / len(scenario_counts)
            
            results['scenario_analysis'][scenario_name] = {
                'mean_count': mean_count,
                'std_count': std_count,
                'min_count': min_count,
                'max_count': max_count,
                'coefficient_of_variation': cv,
                'coverage_rate': coverage,
                'expected_count': expected_per_scenario
            }
        
        # Overall statistics
        total_counts = []
        for dist in distributions:
            total_count = sum(dist.values())
            total_counts.append(total_count)
        
        results['overall_stats'] = {
            'mean_total_users': self.calculate_mean(total_counts),
            'std_total_users': self.calculate_std(total_counts),
            'min_total_users': min(total_counts) if total_counts else 0,
            'max_total_users': max(total_counts) if total_counts else 0,
            'target_users': expected_per_scenario * 8
        }
        
        return results

    def compare_distributions(self, users_15, users_30):
        """Compare distribution quality between 15 and 30 users per session"""
        print("=" * 80)
        print("SCENARIO DISTRIBUTION ANALYSIS")
        print("=" * 80)
        
        # Simulate distributions
        print(f"\n📊 Simulating 100 sessions with 15 users per session...")
        dist_15 = self.simulate_random_distribution(15, 100)
        
        print(f"📊 Simulating 100 sessions with 30 users per session...")
        dist_30 = self.simulate_random_distribution(30, 100)
        
        # Analyze distributions
        print(f"\n🔍 Analyzing distribution quality...")
        analysis_15 = self.analyze_distribution_quality(dist_15, 15/8)
        analysis_30 = self.analyze_distribution_quality(dist_30, 30/8)
        
        # Print comparison
        print(f"\n📈 DISTRIBUTION COMPARISON")
        print(f"{'Scenario':<20} {'15 Users':<15} {'30 Users':<15} {'Improvement':<15}")
        print("-" * 65)
        
        for i, scenario_name in enumerate(self.scenario_labels):
            stats_15 = analysis_15['scenario_analysis'][scenario_name]
            stats_30 = analysis_30['scenario_analysis'][scenario_name]
            
            cv_15 = stats_15['coefficient_of_variation']
            cv_30 = stats_30['coefficient_of_variation']
            
            improvement = ((cv_15 - cv_30) / cv_15 * 100) if cv_15 > 0 else 0
            
            print(f"{scenario_name:<20} {cv_15:.3f}         {cv_30:.3f}         {improvement:+.1f}%")
        
        # Overall statistics
        print(f"\n📊 OVERALL STATISTICS")
        print(f"15 Users per Session:")
        print(f"  - Expected per scenario: {analysis_15['expected_per_scenario']:.2f}")
        print(f"  - Mean total users: {analysis_15['overall_stats']['mean_total_users']:.1f}")
        print(f"  - Standard deviation: {analysis_15['overall_stats']['std_total_users']:.1f}")
        
        print(f"\n30 Users per Session:")
        print(f"  - Expected per scenario: {analysis_30['expected_per_scenario']:.2f}")
        print(f"  - Mean total users: {analysis_30['overall_stats']['mean_total_users']:.1f}")
        print(f"  - Standard deviation: {analysis_30['overall_stats']['std_total_users']:.1f}")
        
        # Calculate improvement in distribution quality
        avg_cv_15 = self.calculate_mean([stats['coefficient_of_variation'] for stats in analysis_15['scenario_analysis'].values()])
        avg_cv_30 = self.calculate_mean([stats['coefficient_of_variation'] for stats in analysis_30['scenario_analysis'].values()])
        
        improvement_percent = ((avg_cv_15 - avg_cv_30) / avg_cv_15 * 100) if avg_cv_15 > 0 else 0
        
        print(f"\n🎯 DISTRIBUTION QUALITY IMPROVEMENT:")
        print(f"  - 15 users: Average CV = {avg_cv_15:.3f}")
        print(f"  - 30 users: Average CV = {avg_cv_30:.3f}")
        print(f"  - Improvement: {improvement_percent:+.1f}%")
        
        return {
            'analysis_15': analysis_15,
            'analysis_30': analysis_30,
            'improvement_percent': improvement_percent
        }

    def test_actual_distribution(self, num_users=30, num_sessions=10):
        """Test actual distribution with real random selection"""
        print(f"\n🧪 TESTING ACTUAL DISTRIBUTION")
        print(f"Users per session: {num_users}")
        print(f"Number of sessions: {num_sessions}")
        print(f"Expected per scenario: {num_users/8:.2f}")
        
        session_results = []
        
        for session in range(num_sessions):
            session_scenarios = []
            for user in range(num_users):
                scenario = random.choice(self.scenarios)
                scenario_index = self.scenarios.index(scenario)
                session_scenarios.append(scenario_index)
            
            distribution = Counter(session_scenarios)
            session_results.append(dict(distribution))
            
            print(f"\nSession {session + 1}:")
            for i, scenario_name in enumerate(self.scenario_labels):
                count = distribution.get(i, 0)
                expected = num_users / 8
                deviation = count - expected
                print(f"  {scenario_name}: {count} (expected: {expected:.1f}, deviation: {deviation:+.1f})")
        
        return session_results

def main():
    """Main function to run the distribution analysis"""
    analyzer = SimpleScenarioAnalyzer()
    
    print("🎲 SCENARIO DISTRIBUTION ANALYSIS")
    print("Analyzing randomness quality for 15 vs 30 users per session")
    
    # Compare distributions
    comparison = analyzer.compare_distributions(15, 30)
    
    # Test actual distribution
    print("\n" + "=" * 80)
    test_results = analyzer.test_actual_distribution(30, 5)
    
    # Save results
    results = {
        'comparison': comparison,
        'test_results': test_results,
        'scenarios': analyzer.scenarios,
        'scenario_labels': analyzer.scenario_labels
    }
    
    with open('scenario_distribution_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: scenario_distribution_results.json")
    
    # Final recommendation
    print(f"\n🎯 RECOMMENDATION:")
    if comparison['improvement_percent'] > 0:
        print(f"✅ 30 users per session provides BETTER distribution quality")
        print(f"   Improvement: {comparison['improvement_percent']:+.1f}%")
    else:
        print(f"⚠️  15 users per session provides better distribution quality")
        print(f"   Consider sticking with 15 users per session")

if __name__ == "__main__":
    main() 
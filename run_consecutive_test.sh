#!/bin/bash

# Consecutive Memory Management Test Runner
# Tests the new memory management improvements with 10 consecutive batches of 15 users each

echo "🚀 Starting Consecutive Memory Management Test"
echo "📊 Testing: 10 consecutive batches with 15 users each"
echo "🎯 Total Users: 150"
echo "⏰ Start Time: $(date)"
echo "=" * 60

# Check if the test script exists
if [ ! -f "consecutive_memory_test.py" ]; then
    echo "❌ Error: consecutive_memory_test.py not found"
    exit 1
fi

# Check if we can connect to the server
echo "🔍 Checking server connectivity..."
if ! curl -s --connect-timeout 10 http://3.144.114.76:8000/api/chatbot/initial/ > /dev/null; then
    echo "❌ Error: Cannot connect to server at http://3.144.114.76:8000"
    echo "💡 Make sure the server is running and accessible"
    exit 1
fi

echo "✅ Server is accessible"

# Check SSH key
if [ ! -f ~/.ssh/combot-key.pem ]; then
    echo "⚠️  Warning: SSH key not found at ~/.ssh/combot-key.pem"
    echo "💡 Memory monitoring will be limited"
fi

# Create results directory
mkdir -p test_results
cd test_results

# Run the test
echo "🔄 Starting consecutive memory test..."
python3 ../consecutive_memory_test.py

# Check if test completed successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Test completed successfully!"
    echo "📄 Results saved to: test_results/consecutive_memory_test_results.json"
    echo "📋 Log saved to: test_results/consecutive_memory_test.log"
    
    # Show summary if results file exists
    if [ -f "consecutive_memory_test_results.json" ]; then
        echo ""
        echo "📊 QUICK SUMMARY:"
        echo "=================="
        
        # Extract key metrics using jq if available
        if command -v jq &> /dev/null; then
            total_users=$(jq '.test_info.total_users' consecutive_memory_test_results.json)
            success_rate=$(jq '.overall_stats.success_rate' consecutive_memory_test_results.json)
            avg_response_time=$(jq '.overall_stats.avg_response_time' consecutive_memory_test_results.json)
            total_duration=$(jq '.test_info.total_duration' consecutive_memory_test_results.json)
            
            echo "Total Users: $total_users"
            echo "Success Rate: ${success_rate}%"
            echo "Avg Response Time: ${avg_response_time}s"
            echo "Total Duration: ${total_duration}s"
        else
            echo "Install jq for detailed results parsing: sudo apt-get install jq"
        fi
    fi
else
    echo "❌ Test failed!"
    echo "📋 Check the log file for details: test_results/consecutive_memory_test.log"
    exit 1
fi

echo ""
echo "⏰ End Time: $(date)"
echo "🎉 Consecutive memory test completed!" 
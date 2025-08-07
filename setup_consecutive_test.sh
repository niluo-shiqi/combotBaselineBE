#!/bin/bash

# Setup script for Consecutive Memory Test
# Prepares the environment and checks prerequisites

echo "🔧 Setting up Consecutive Memory Test"
echo "=" * 40

# Check Python dependencies
echo "📦 Checking Python dependencies..."
python3 -c "import requests, json, time, logging, threading, psutil, subprocess" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ All Python dependencies are available"
else
    echo "❌ Missing Python dependencies"
    echo "💡 Install with: pip3 install requests psutil"
    exit 1
fi

# Check if test files exist
echo "📁 Checking test files..."
if [ -f "consecutive_memory_test.py" ]; then
    echo "✅ consecutive_memory_test.py found"
else
    echo "❌ consecutive_memory_test.py not found"
    exit 1
fi

if [ -f "monitor_consecutive_test.py" ]; then
    echo "✅ monitor_consecutive_test.py found"
else
    echo "❌ monitor_consecutive_test.py not found"
    exit 1
fi

# Check server connectivity
echo "🌐 Checking server connectivity..."
if curl -s --connect-timeout 10 http://3.144.114.76:8000/api/chatbot/initial/ > /dev/null; then
    echo "✅ Server is accessible"
else
    echo "❌ Cannot connect to server"
    echo "💡 Make sure the server is running at http://3.144.114.76:8000"
    exit 1
fi

# Check SSH key for memory monitoring
if [ -f ~/.ssh/combot-key.pem ]; then
    echo "✅ SSH key found for memory monitoring"
    chmod 600 ~/.ssh/combot-key.pem
else
    echo "⚠️  SSH key not found at ~/.ssh/combot-key.pem"
    echo "💡 Memory monitoring will be limited"
fi

# Create results directory
mkdir -p test_results
echo "✅ Created test_results directory"

# Make scripts executable
chmod +x run_consecutive_test.sh
chmod +x monitor_consecutive_test.py
echo "✅ Made scripts executable"

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Run the test: ./run_consecutive_test.sh"
echo "2. Monitor progress: python3 monitor_consecutive_test.py"
echo "3. View results: cat test_results/consecutive_memory_test_results.json"
echo ""
echo "🚀 Ready to test the memory management improvements!" 
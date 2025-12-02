#!/bin/bash

# Script to Images - Startup Script

echo "🚀 Starting Script to Images Application..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install backend dependencies
echo "📥 Installing backend dependencies..."
pip install -r requirements.txt

# Install frontend dependencies
echo "📱 Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Start backend server in background
echo "🖥️  Starting backend server..."
python backend/app.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend development server
echo "🌐 Starting frontend development server..."
cd frontend
npm run dev &
FRONTEND_PID=$!

# Wait for user to stop
echo ""
echo "✅ Application started successfully!"
echo "📊 Backend API: http://localhost:5000"
echo "🎨 Frontend UI:  http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers..."

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "👋 Application stopped."
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Wait for processes
wait

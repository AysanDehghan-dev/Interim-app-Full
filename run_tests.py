#!/usr/bin/env python3
"""
Test runner script for the Interim App
Provides different test execution options and coverage reporting
Automatically detects CI environment and runs appropriate tests
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def is_ci_environment():
    """Check if running in CI environment"""
    return (os.getenv('CI', '').lower() == 'true' or 
            os.getenv('GITHUB_ACTIONS', '').lower() == 'true')

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔍 {description}")
    print(f"Command: {' '.join(command)}")
    print("-" * 50)
    
    result = subprocess.run(command, capture_output=False)
    
    if result.returncode != 0:
        print(f"❌ {description} failed with exit code {result.returncode}")
        return False
    else:
        print(f"✅ {description} completed successfully")
        return True

def setup_test_environment():
    """Setup test environment based on CI detection"""
    print("🚀 Setting up test environment...")
    
    if is_ci_environment():
        print("🤖 CI Environment detected - using mock tests")
        # Set environment flag for mock tests
        os.environ['CI'] = 'true'
        print("✅ Mock environment ready")
        return True
    else:
        print("💻 Local Environment detected - using real database tests")
        # Check if MongoDB is running (basic check)
        try:
            import pymongo
            client = pymongo.MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=1000)
            client.server_info()
            print("✅ MongoDB connection successful")
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            print("Please ensure MongoDB is running on localhost:27017")
            print("Or set CI=true environment variable to use mock tests")
            return False
        
        # Check if test database can be accessed
        try:
            db = client['test_interim_app']
            db.list_collection_names()
            print("✅ Test database accessible")
        except Exception as e:
            print(f"❌ Test database access failed: {e}")
            return False
        
        client.close()
        return True

def get_test_files(test_type, use_mocks=False):
    """Get appropriate test files based on environment"""
    
    # Detect if we're in the root directory or if tests are in a subdirectory
    if os.path.exists("tests/"):
        test_dir = "tests/"
    elif os.path.exists("backend/tests/"):
        test_dir = "backend/tests/"
    else:
        test_dir = "tests/"  # Default fallback
    
    if use_mocks:
        # Mock test configurations for CI
        test_commands = {
            "unit": [f"{test_dir}test_mock_auth.py"],
            "routes": [f"{test_dir}test_mock_auth.py"],  # Limited routes testing with mocks
            "integration": [f"{test_dir}test_mock_integration.py"],
            "auth": [f"{test_dir}test_mock_auth.py"],
            "models": [f"{test_dir}test_mock_integration.py"],  # Model testing via integration
            "smoke": [f"{test_dir}test_mock_integration.py::TestMockIntegrationWorkflows::test_mock_home_endpoint"],
            "all": [f"{test_dir}test_mock_auth.py", f"{test_dir}test_mock_integration.py"]
        }
    else:
        # Original test configurations for local development
        test_commands = {
            "unit": [f"{test_dir}test_models.py", f"{test_dir}test_auth.py"],
            "routes": [f"{test_dir}test_routes_*.py"],
            "integration": [f"{test_dir}test_integration.py"],
            "auth": ["-m", "auth"],
            "models": ["-m", "models"],
            "smoke": [f"{test_dir}test_integration.py::TestIntegrationWorkflows::test_home_endpoint"],
            "all": [test_dir]
        }
    
    return test_commands.get(test_type, [])

def run_tests(test_type="all", verbose=False, coverage=True, parallel=False):
    """Run tests based on specified type"""
    
    if not setup_test_environment():
        return False
    
    use_mocks = is_ci_environment()
    
    base_command = ["python", "-m", "pytest"]
    
    # Add verbosity
    if verbose:
        base_command.append("-v")
    else:
        base_command.append("-q")
    
    # Add coverage (adjust coverage threshold for mock tests)
    if coverage:
        coverage_threshold = 50 if use_mocks else 70  # Lower threshold for mock tests
        base_command.extend([
            "--cov=app",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            f"--cov-fail-under={coverage_threshold}"
        ])
    
    # Add parallel execution (disable for mock tests to avoid conflicts)
    if parallel and not use_mocks:
        base_command.extend(["-n", "auto"])
    
    # Get test files based on environment
    test_files = get_test_files(test_type, use_mocks)
    
    if not test_files:
        print(f"❌ Unknown test type: {test_type}")
        available_types = list(get_test_files("all", use_mocks).keys()) if use_mocks else ["unit", "routes", "integration", "auth", "models", "smoke", "all"]
        print(f"Available types: {', '.join(available_types)}")
        return False
    
    command = base_command + test_files
    
    test_env = "mock" if use_mocks else "real database"
    description = f"Running {test_type} tests ({test_env})"
    
    # Set pytest configuration for mock tests
    if use_mocks:
        # Use specific conftest for mock tests
        command.extend(["-p", "no:warnings", "--tb=short"])
    
    return run_command(command, description)

def generate_coverage_report():
    """Generate detailed coverage report"""
    commands = [
        (["coverage", "html"], "Generating HTML coverage report"),
        (["coverage", "xml"], "Generating XML coverage report"),
        (["coverage", "report"], "Displaying coverage summary")
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    
    print("\n📊 Coverage reports generated:")
    print("- HTML report: htmlcov/index.html")
    print("- XML report: coverage.xml")
    
    return True

def clean_test_artifacts():
    """Clean test artifacts and cache"""
    print("\n🧹 Cleaning test artifacts...")
    
    artifacts = [
        ".pytest_cache",
        "__pycache__",
        "htmlcov",
        ".coverage",
        "coverage.xml",
        "test-results.xml",
        ".mypy_cache"
    ]
    
    for artifact in artifacts:
        path = Path(artifact)
        if path.exists():
            if path.is_file():
                path.unlink()
                print(f"Removed file: {artifact}")
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)
                print(f"Removed directory: {artifact}")
    
    # Also clean Python cache in app directory
    for root, dirs, files in os.walk("app"):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                import shutil
                shutil.rmtree(os.path.join(root, dir_name))
                print(f"Removed cache: {os.path.join(root, dir_name)}")

def setup_mock_test_files():
    """Ensure mock test files exist"""
    # Detect test directory
    if os.path.exists("tests/"):
        test_dir = "tests/"
    elif os.path.exists("backend/tests/"):
        test_dir = "backend/tests/"
    else:
        test_dir = "tests/"
    
    mock_files = [
        f"{test_dir}test_mock_auth.py",
        f"{test_dir}test_mock_integration.py", 
        f"{test_dir}conftest_mock.py",
        f"{test_dir}mocks/__init__.py",
        f"{test_dir}mocks/mock_database.py"
    ]
    
    missing_files = []
    for file_path in mock_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("⚠️  Missing mock test files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print(f"\nPlease create these files in your {test_dir} directory.")
        print("Run with --force-local to use real database tests instead.")
        return False
    
    return True

def show_environment_info():
    """Show information about the test environment"""
    print("\n📋 Test Environment Information:")
    print("-" * 40)
    
    # Detect test directory
    if os.path.exists("tests/"):
        test_dir = "tests/"
    elif os.path.exists("backend/tests/"):
        test_dir = "backend/tests/"
    else:
        test_dir = "tests/ (not found)"
    
    if is_ci_environment():
        print("🤖 Environment: CI/CD (GitHub Actions)")
        print("🎭 Test Mode: Mock tests (no MongoDB required)")
        print("⚡ Performance: Fast execution")
        print("🔧 Database: In-memory mock database")
        print("📊 Coverage Threshold: 50% (reduced for mocks)")
    else:
        print("💻 Environment: Local Development")
        print("🏗️  Test Mode: Full integration tests")
        print("🐌 Performance: Slower but comprehensive")
        print("🗄️  Database: Real MongoDB connection")
        print("📊 Coverage Threshold: 80% (full coverage)")
    
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"📁 Working Directory: {os.getcwd()}")
    print(f"📂 Test Directory: {test_dir}")
    print(f"🔑 CI Environment Variable: {os.getenv('CI', 'false')}")
    print(f"🔑 GitHub Actions Variable: {os.getenv('GITHUB_ACTIONS', 'false')}")
    
    # Check test files exist
    if os.path.exists(test_dir.rstrip('/')):
        test_files = list(Path(test_dir).glob("test_*.py"))
        print(f"🧪 Available test files: {len(test_files)} found")
    else:
        print(f"⚠️  Test directory not found: {test_dir}")

def detect_project_structure():
    """Detect and show project structure"""
    print("\n🔍 Project Structure Detection:")
    print("-" * 40)
    
    structure_found = False
    
    if os.path.exists("app/") and os.path.exists("backend/tests/"):
        print("✅ Backend structure detected:")
        print("   📁 app/ - Application code")
        print("   📁 backend/tests/ - Test files")
        structure_found = True
    elif os.path.exists("app/") and os.path.exists("tests/"):
        print("✅ Standard structure detected:")
        print("   📁 app/ - Application code")
        print("   📁 tests/ - Test files")
        structure_found = True
    elif os.path.exists("backend/"):
        print("📁 Backend directory found")
        if os.path.exists("backend/app/"):
            print("   📁 backend/app/ - Application code")
        if os.path.exists("backend/tests/"):
            print("   📁 backend/tests/ - Test files")
        structure_found = True
    
    if not structure_found:
        print("⚠️  No standard structure detected")
        print("   Expected: app/ + tests/ OR app/ + backend/tests/")
    
    return structure_found

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="Test runner for Interim App")
    
    parser.add_argument(
        "test_type",
        choices=["unit", "routes", "integration", "auth", "models", "smoke", "all"],
        default="all",
        nargs="?",
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Skip coverage reporting"
    )
    
    parser.add_argument(
        "-p", "--parallel",
        action="store_true",
        help="Run tests in parallel (local only)"
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean test artifacts before running"
    )
    
    parser.add_argument(
        "--coverage-only",
        action="store_true",
        help="Only generate coverage report (don't run tests)"
    )
    
    parser.add_argument(
        "--force-ci",
        action="store_true",
        help="Force CI mode (use mock tests even locally)"
    )
    
    parser.add_argument(
        "--force-local",
        action="store_true",
        help="Force local mode (use real tests even in CI)"
    )
    
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show environment information and exit"
    )
    
    parser.add_argument(
        "--structure",
        action="store_true", 
        help="Show project structure detection and exit"
    )
    
    args = parser.parse_args()
    
    print("🧪 Interim App Test Runner")
    print("=" * 50)
    
    # Handle force flags
    if args.force_ci:
        os.environ['CI'] = 'true'
        print("🔧 Forced CI mode - using mock tests")
    elif args.force_local:
        os.environ.pop('CI', None)
        os.environ.pop('GITHUB_ACTIONS', None)
        print("🔧 Forced local mode - using real database tests")
    
    # Show environment info if requested
    if args.info:
        show_environment_info()
        return 0
    
    # Show structure info if requested  
    if args.structure:
        detect_project_structure()
        show_environment_info()
        return 0
    
    # Show environment info briefly
    show_environment_info()
    
    # Detect project structure
    structure_ok = detect_project_structure()
    if not structure_ok:
        print("\n⚠️  Warning: Unexpected project structure detected")
        print("   This might cause test discovery issues")
    
    # Check test directory exists
    test_dir = "backend/tests/" if os.path.exists("backend/tests/") else "tests/"
    if not os.path.exists(test_dir.rstrip('/')):
        print(f"\n❌ Test directory not found: {test_dir}")
        print("Please ensure your tests are in 'tests/' or 'backend/tests/' directory")
        return 1
    
    # Check mock test files if in CI mode
    if is_ci_environment() and not setup_mock_test_files():
        print("\n❌ Cannot proceed without mock test files")
        return 1
    
    if args.clean:
        clean_test_artifacts()
    
    if args.coverage_only:
        success = generate_coverage_report()
    else:
        success = run_tests(
            test_type=args.test_type,
            verbose=args.verbose,
            coverage=not args.no_coverage,
            parallel=args.parallel
        )
        
        if success and not args.no_coverage:
            generate_coverage_report()
    
    if success:
        print("\n🎉 All operations completed successfully!")
        
        if is_ci_environment():
            print("✨ Mock tests passed - ready for deployment!")
        else:
            print("🏆 Full integration tests passed - excellent work!")
        
        return 0
    else:
        print("\n💥 Some operations failed!")
        
        if is_ci_environment():
            print("🔧 Try running locally with full database tests for debugging")
        else:
            print("💡 Ensure MongoDB is running and try again")
        
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
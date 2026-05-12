import os
import sys

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Add current directory to path
sys.path.insert(0, ".")

from jerry.tools.web_search import WebSearchTool
from jerry.tools.file_ops import CopyFileTool, MoveFileTool, DeleteFileTool

def test_web_search():
    print("\n--- WEB SEARCH TEST ---")
    ws = WebSearchTool()
    result = ws.execute("python 3.12 release date", max_results=1)
    print(result)

def test_file_ops():
    print("\n--- FILE OPS TEST ---")
    
    # Create test file
    test_file = "test_jerry_v2.txt"
    with open(test_file, "w") as f:
        f.write("Hello from Phase 2!")
    print(f"✅ Created {test_file}")
    
    # Test Copy
    params_copy = {"source": test_file, "destination": "test_copy.txt"}
    cp = CopyFileTool()
    print(cp.execute(**params_copy))
    
    # Test Move
    params_move = {"source": "test_copy.txt", "destination": "test_moved.txt"}
    mv = MoveFileTool()
    print(mv.execute(**params_move))
    
    # Test Delete
    dl = DeleteFileTool()
    print(dl.execute(test_file, confirm=True))
    print(dl.execute("test_moved.txt", confirm=True))
    
    print("✅ File ops tests complete")

if __name__ == "__main__":
    try:
        test_web_search()
        test_file_ops()
    except Exception as e:
        print(f"❌ Test Failed: {e}")

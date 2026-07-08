import os
import sys

def build_tree(startpath):
    ignored = {
        '.git', 'node_modules', '__pycache__', '.tanstack', '.wrangler', 
        '.output', '.lovable', 'yolov8s.pt'
    }
    
    out = []
    for root, dirs, files in os.walk(startpath):
        # Filter ignored directories in-place so os.walk doesn't traverse them
        dirs[:] = [d for d in dirs if d not in ignored]
        
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * level
        out.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in sorted(files):
            if f in ignored:
                continue
            filepath = os.path.join(root, f)
            try:
                size = os.path.getsize(filepath)
                # Count lines for text files
                lines = 0
                if f.endswith(('.py', '.ts', '.tsx', '.json', '.js', '.css', '.html', '.md', '.ini', '.toml', '.env')):
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
                        lines = len(fh.readlines())
                line_str = f" ({lines} lines)" if lines > 0 else ""
                size_str = f"{size / 1024:.2f} KB" if size >= 1024 else f"{size} B"
                out.append(f"{subindent}{f} - {size_str}{line_str}")
            except Exception as e:
                out.append(f"{subindent}{f} - Error: {e}")
                
    return "\n".join(out)

if __name__ == "__main__":
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(f"Project Workspace Root: {workspace_root}\n")
    print(build_tree(workspace_root))

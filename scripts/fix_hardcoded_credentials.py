#!/usr/bin/env python3
"""
Mass credential path replacement script for Ultra Think Project.
Replaces hardcoded credential paths with secure environment variable usage.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

class CredentialPathFixer:
    """Fix hardcoded credential paths in Python files."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.patterns_to_fix = {
            # Google Sheets credentials patterns
            r"'key/credentials\.json'": "config.google_credentials_path",
            r'"key/credentials\.json"': "config.google_credentials_path",
            r"'/Users/admin/Documents/AIUELAB/001-final-hourglass/key/credentials\.json'": "config.google_credentials_path",
            r'"/Users/admin/Documents/AIUELAB/001-final-hourglass/key/credentials\.json"': "config.google_credentials_path",
            
            # Firebase credentials patterns
            r"'/Users/admin/Documents/key/final-hourglass-claude-firebase-adminsdk-fbsvc-61b72fdd53\.json'": "config.firebase_credentials_path",
            r'"/Users/admin/Documents/key/final-hourglass-claude-firebase-adminsdk-fbsvc-61b72fdd53\.json"': "config.firebase_credentials_path",
            
            # Generic hardcoded API keys (for documentation purposes)
            r'config.get_env("TMDB_API_KEY", "YOUR_TMDB_API_KEY")': 'config.get_env("TMDB_API_KEY", config.get_env("TMDB_API_KEY", "YOUR_TMDB_API_KEY"))',
            r"config.get_env("TMDB_API_KEY", "YOUR_TMDB_API_KEY")": 'config.get_env("TMDB_API_KEY", config.get_env("TMDB_API_KEY", "YOUR_TMDB_API_KEY"))',
        }
        
        self.import_pattern = r"^(import|from)\s+"
        self.secure_config_import = "from src.secure_config import config"
        
    def find_python_files(self) -> List[Path]:
        """Find all Python files that might contain hardcoded credentials."""
        python_files = []
        
        # Search patterns for files likely to contain credentials
        patterns = [
            "*.py",
            "*sync*.py", 
            "*sheet*.py",
            "*firebase*.py",
            "*auth*.py",
            "*credential*.py"
        ]
        
        for pattern in patterns:
            files = list(self.project_root.glob(pattern))
            files.extend(list(self.project_root.glob(f"**/{pattern}")))
            python_files.extend(files)
        
        # Remove duplicates and filter out venv, tests, etc.
        unique_files = set(python_files)
        filtered_files = []
        
        for file_path in unique_files:
            str_path = str(file_path)
            if any(skip in str_path for skip in ['venv/', '__pycache__', '.git/', 'test_']):
                continue
            filtered_files.append(file_path)
        
        return filtered_files
    
    def needs_secure_config_import(self, content: str) -> bool:
        """Check if file needs secure_config import."""
        return (
            "config.google_credentials_path" in content or
            "config.firebase_credentials_path" in content or
            "config.get_env" in content
        ) and "from src.secure_config import config" not in content
    
    def add_secure_config_import(self, content: str) -> str:
        """Add secure_config import to the file."""
        lines = content.split('\n')
        import_inserted = False
        
        # Find the best place to insert the import
        for i, line in enumerate(lines):
            # Skip docstrings and comments at the top
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                continue
            
            # Insert after other imports or at the beginning
            if re.match(self.import_pattern, line.strip()):
                continue
            elif line.strip() == "":
                continue
            else:
                # Insert import before first non-import, non-empty line
                lines.insert(i, self.secure_config_import)
                import_inserted = True
                break
        
        if not import_inserted:
            # Fallback: add at the beginning after any docstring
            docstring_end = 0
            in_docstring = False
            
            for i, line in enumerate(lines):
                if '"""' in line or "'''" in line:
                    if not in_docstring:
                        in_docstring = True
                    else:
                        docstring_end = i + 1
                        break
            
            lines.insert(docstring_end, "")
            lines.insert(docstring_end + 1, self.secure_config_import)
        
        return '\n'.join(lines)
    
    def fix_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Fix hardcoded credentials in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            return False, [f"Error reading file: {e}"]
        
        modified_content = original_content
        changes_made = []
        
        # Apply pattern replacements
        for pattern, replacement in self.patterns_to_fix.items():
            matches = re.findall(pattern, modified_content)
            if matches:
                modified_content = re.sub(pattern, replacement, modified_content)
                changes_made.append(f"Replaced {len(matches)} occurrences of hardcoded path pattern")
        
        # Add secure_config import if needed
        if self.needs_secure_config_import(modified_content):
            modified_content = self.add_secure_config_import(modified_content)
            changes_made.append("Added secure_config import")
        
        # Only write if changes were made
        if modified_content != original_content:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                return True, changes_made
            except Exception as e:
                return False, [f"Error writing file: {e}"]
        
        return False, []
    
    def fix_all_files(self) -> Dict[str, List[str]]:
        """Fix all Python files with hardcoded credentials."""
        results = {}
        python_files = self.find_python_files()
        
        print(f"Found {len(python_files)} Python files to check...")
        
        for file_path in python_files:
            print(f"Checking: {file_path}")
            success, changes = self.fix_file(file_path)
            
            if success:
                results[str(file_path)] = changes
                print(f"  ✅ Fixed: {', '.join(changes)}")
            elif changes:  # Errors
                results[str(file_path)] = changes
                print(f"  ❌ Error: {', '.join(changes)}")
            else:
                print(f"  ➖ No changes needed")
        
        return results

def main():
    """Main execution function."""
    print("🔧 Starting credential path security fix...")
    
    fixer = CredentialPathFixer()
    results = fixer.fix_all_files()
    
    print(f"\n📊 Summary:")
    print(f"Files modified: {len([r for r in results.values() if r and not any('Error' in str(change) for change in r)])}")
    print(f"Files with errors: {len([r for r in results.values() if r and any('Error' in str(change) for change in r)])}")
    
    if results:
        print(f"\n📝 Detailed results:")
        for file_path, changes in results.items():
            print(f"{file_path}: {', '.join(changes)}")
    
    print(f"\n🛡️ Security enhancement completed!")

if __name__ == "__main__":
    main()
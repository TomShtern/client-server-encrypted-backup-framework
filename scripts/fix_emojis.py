#!/usr/bin/env python3
"""
Quick script to fix emoji characters in benchmark files for Windows console compatibility
"""

import re

def fix_emojis_in_file(filename):
    """Replace emoji characters with ASCII equivalents"""
    
    emoji_replacements = {
        '🔨': '[BUILD]',
        '🚀': '[START]',
        '🛑': '[STOP]',
        '⚡': '[RUN]',
        '💻': '[SYS]',
        '🐍': '[PY]',
        '❌': '[FAIL]',
        '✅': '[OK]',
        '⚠️': '[WARN]',
        '🎯': '[TARGET]',
        '📊': '[DATA]',
        '🎉': '[SUCCESS]',
        '📈': '[METRICS]',
        '🔧': '[FIX]',
        '📋': '[INFO]',
        '⏳': '[WAIT]',
        '💾': '[SAVE]',
        '🔍': '[CHECK]',
        '🔗': '[CONN]',
        '📨': '[MSG]',
        '🔀': '[MULTI]',
        '🌐': '[NET]',
        '📡': '[SIGNAL]',
        '📅': '[DATE]',
        '📁': '[FOLDER]',
        '🔐': '[CRYPTO]',
        '🔒': '[ENCRYPT]',
        '💡': '[TIP]'
    }
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace emojis
        for emoji, replacement in emoji_replacements.items():
            content = content.replace(emoji, replacement)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[OK] Fixed emojis in {filename}")
        return True
        
    except Exception as e:
        print(f"[FAIL] Error fixing {filename}: {e}")
        return False

if __name__ == "__main__":
    files_to_fix = [
        "run_all_benchmarks.py",
        "client_benchmark.cpp"
    ]
    
    for filename in files_to_fix:
        fix_emojis_in_file(filename)
    
    print("[OK] Emoji fix completed!")

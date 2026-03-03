from pathlib import Path
p = Path(r"C:\Users\signa\OneDrive\Desktop\Agent X\audio_manager.py")
s = p.read_text(encoding='utf-8')
lines = s.splitlines()
# Find the line with eager VAD creation
for i,l in enumerate(lines):
    if 'self.vad = VADProcessor' in l:
        lines[i] = '        self.vad = None'
        break
else:
    print('Eager VAD creation not found')

# Find test_mode assignment and insertion point
for i,l in enumerate(lines):
    if 'self.test_mode = bool(test_mode)' in l:
        # find the next line with 'if self.test_mode' and then the following line where vad_enabled is set
        insert_at = None
        for j in range(i, i+6):
            if j < len(lines) and lines[j].strip().startswith('if self.test_mode'):
                # insert after the block (find end of that simple block)
                # typically next line is '    self.vad_enabled = False'
                insert_at = j+2
                break
        if insert_at is None:
            insert_at = i+2
        lazy = [
            '        # Initialize VAD processor lazily when not in test_mode',
            '        if not self.test_mode:',
            "            try:",
            "                self.vad = VADProcessor(threshold=self.vad_threshold)",
            "            except Exception as e:",
            "                logger.warning(f\"VAD initialization failed: {e}\")",
            "                self.vad = None",
            "                self.vad_enabled = False",
        ]
        for k,ln in enumerate(reversed(lazy)):
            lines.insert(insert_at, lazy[-(k+1)])
        break

p.write_text('\n'.join(lines), encoding='utf-8')
print('Patched audio_manager.py')

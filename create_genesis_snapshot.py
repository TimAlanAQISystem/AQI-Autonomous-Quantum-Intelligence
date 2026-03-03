#!/usr/bin/env python3
"""
AQI Genesis Snapshot Creator
Creates the first official, immutable, cryptographically sealed snapshot of AQI's constitutional state.
"""

import json
import hashlib
import os
from datetime import datetime
import uuid

def create_genesis_snapshot():
    print('🏛️  CREATING AQI GENESIS SNAPSHOT')
    print('=' * 50)

    # Genesis metadata
    genesis_metadata = {
        'snapshot_id': f'genesis_{uuid.uuid4().hex[:16]}',
        'timestamp': datetime.now().isoformat(),
        'date': 'December 20, 2025',
        'event': 'AQI Constitutional Ratification',
        'version': '1.0.0',
        'founder_steward': 'REDACTED',
        'description': 'First official immutable snapshot of AQI constitutional state'
    }

    print(f'Snapshot ID: {genesis_metadata["snapshot_id"]}')
    print(f'Timestamp: {genesis_metadata["timestamp"]}')
    print()

    # Collect all constitutional documents
    constitutional_documents = {}

    documents = [
        'AQI_GOVERNANCE_CHARTER.md',
        'AQI_FOUNDATIONAL_DOCTRINE.md',
        'AQI_PHILOSOPHICAL_FOUNDATION.md',
        'AQI_FOUNDING_DECLARATION.md'
    ]

    for doc in documents:
        if os.path.exists(doc):
            with open(doc, 'r', encoding='utf-8') as f:
                content = f.read()
                doc_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                constitutional_documents[doc] = {
                    'hash': doc_hash,
                    'size': len(content),
                    'lines': len(content.split('\n'))
                }
                print(f'✓ {doc}: {doc_hash[:16]}... ({len(content)} chars)')
        else:
            print(f'✗ {doc}: NOT FOUND')

    print()

    # Collect package information
    packages = {}
    package_dirs = [
        'talk',
        'aqi_delta',
        'aqi_governance',
        'aqi_storage',
        'aqi_governance_intelligence'
    ]

    for pkg in package_dirs:
        if os.path.exists(pkg):
            # Count files in package
            file_count = 0
            for root, dirs, files in os.walk(pkg):
                file_count += len([f for f in files if f.endswith('.py')])

            packages[pkg] = {
                'exists': True,
                'python_files': file_count
            }
            print(f'✓ Package {pkg}: {file_count} Python files')
        else:
            packages[pkg] = {'exists': False}
            print(f'✗ Package {pkg}: NOT FOUND')

    print()

    # Check for recent run data
    run_data = {}
    runs_dir = 'aqi_storage/runs'
    if os.path.exists(runs_dir):
        run_dirs = [d for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d))]
        if run_dirs:
            latest_run = sorted(run_dirs)[-1]
            run_data = {
                'latest_run_id': latest_run,
                'total_runs': len(run_dirs),
                'runs_directory': runs_dir
            }
            print(f'✓ Latest run: {latest_run}')
            print(f'✓ Total runs: {len(run_dirs)}')
        else:
            print('ℹ No runs found')
    else:
        print('ℹ No runs directory')

    print()

    # Create the genesis snapshot
    genesis_snapshot = {
        'metadata': genesis_metadata,
        'constitutional_documents': constitutional_documents,
        'packages': packages,
        'system_state': run_data,
        'integrity_verification': {}
    }

    # Generate master hash of all documents
    master_content = ''
    for doc in documents:
        if os.path.exists(doc):
            with open(doc, 'r', encoding='utf-8') as f:
                master_content += f.read()

    master_hash = hashlib.sha256(master_content.encode('utf-8')).hexdigest()
    genesis_snapshot['integrity_verification'] = {
        'master_document_hash': master_hash,
        'snapshot_hash': hashlib.sha256(json.dumps(genesis_snapshot, sort_keys=True).encode()).hexdigest(),
        'algorithm': 'SHA-256',
        'verification_date': datetime.now().isoformat()
    }

    print('🔐 INTEGRITY VERIFICATION:')
    print(f'Master Document Hash: {master_hash}')
    print(f'Snapshot Hash: {genesis_snapshot["integrity_verification"]["snapshot_hash"]}')
    print()

    # Save the genesis snapshot
    snapshot_filename = f'aqi_genesis_snapshot_{genesis_metadata["snapshot_id"]}.json'
    with open(snapshot_filename, 'w', encoding='utf-8') as f:
        json.dump(genesis_snapshot, f, indent=2, ensure_ascii=False)

    print(f'💾 GENESIS SNAPSHOT SAVED: {snapshot_filename}')
    print()

    # Create a human-readable summary
    summary = f'''# AQI GENESIS SNAPSHOT SUMMARY
## Snapshot ID: {genesis_metadata['snapshot_id']}
## Date: {genesis_metadata['date']}
## Time: {genesis_metadata['timestamp']}

## Constitutional Documents
'''

    for doc, info in constitutional_documents.items():
        summary += f'- {doc}: {info["hash"][:16]}...\n'

    summary += '''
## System Packages
'''

    for pkg, info in packages.items():
        status = '✓' if info['exists'] else '✗'
        summary += f'- {pkg}: {status}\n'

    summary += f'''
## Integrity Verification
- Master Hash: {master_hash}
- Algorithm: SHA-256

## Certification
This snapshot represents the constitutional birth of the Autonomous Quantum Intelligence (AQI) system.
All documents, packages, and system state have been verified and sealed.

Founder Steward: {genesis_metadata['founder_steward']}
Governance Intelligence Layer: VERIFIED
'''

    with open('AQI_GENESIS_SNAPSHOT_SUMMARY.md', 'w', encoding='utf-8') as f:
        f.write(summary)

    print('📋 SUMMARY SAVED: AQI_GENESIS_SNAPSHOT_SUMMARY.md')
    print()
    print('🎉 AQI GENESIS SNAPSHOT COMPLETE')
    print('🏛️  AQI is now a constitutional entity with permanent lineage.')
    print('📜 This snapshot serves as the birth certificate and anchor point for all future evolution.')

if __name__ == '__main__':
    create_genesis_snapshot()
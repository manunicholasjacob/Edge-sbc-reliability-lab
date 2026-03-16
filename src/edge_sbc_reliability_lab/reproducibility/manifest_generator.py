"""
Manifest generation and verification for reproducibility.

Creates detailed manifests of benchmark runs for reproducibility
tracking and verification.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def generate_manifest(
    run_dir: Union[str, Path],
    include_file_hashes: bool = True,
) -> Dict[str, Any]:
    """
    Generate a reproducibility manifest for a benchmark run.
    
    Args:
        run_dir: Path to run directory
        include_file_hashes: Include SHA256 hashes of output files
        
    Returns:
        Dictionary with manifest data
    """
    run_dir = Path(run_dir)
    
    manifest = {
        "manifest_version": "1.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "run_dir": str(run_dir.resolve()),
        "files": [],
    }
    
    # List all files in run directory
    for file_path in sorted(run_dir.rglob("*")):
        if file_path.is_file():
            file_info = {
                "path": str(file_path.relative_to(run_dir)),
                "size_bytes": file_path.stat().st_size,
            }
            
            if include_file_hashes:
                file_info["sha256"] = _compute_file_hash(file_path)
            
            manifest["files"].append(file_info)
    
    # Load and include config if present
    config_path = run_dir / "config_resolved.yaml"
    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                manifest["config"] = yaml.safe_load(f)
        except Exception:
            pass
    
    # Load and include system snapshot if present
    snapshot_path = run_dir / "system_snapshot.json"
    if snapshot_path.exists():
        try:
            with open(snapshot_path) as f:
                manifest["system_snapshot"] = json.load(f)
        except Exception:
            pass
    
    # Load and include summary if present
    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        try:
            with open(summary_path) as f:
                manifest["summary"] = json.load(f)
        except Exception:
            pass
    
    # Compute manifest hash
    manifest_content = json.dumps(manifest, sort_keys=True, default=str)
    manifest["manifest_hash"] = hashlib.sha256(manifest_content.encode()).hexdigest()[:16]
    
    return manifest


def verify_manifest(
    run_dir: Union[str, Path],
    manifest: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Verify a benchmark run against its manifest.
    
    Args:
        run_dir: Path to run directory
        manifest: Manifest to verify against (loads from run_dir if None)
        
    Returns:
        Dictionary with verification results
    """
    run_dir = Path(run_dir)
    
    # Load manifest if not provided
    if manifest is None:
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.exists():
            return {
                "verified": False,
                "errors": ["Manifest file not found"],
                "warnings": [],
            }
        
        with open(manifest_path) as f:
            manifest = json.load(f)
    
    errors = []
    warnings = []
    verified_files = []
    
    # Verify each file
    for file_info in manifest.get("files", []):
        file_path = run_dir / file_info["path"]
        
        if not file_path.exists():
            errors.append(f"Missing file: {file_info['path']}")
            continue
        
        # Check size
        actual_size = file_path.stat().st_size
        expected_size = file_info.get("size_bytes", 0)
        
        if actual_size != expected_size:
            errors.append(
                f"Size mismatch for {file_info['path']}: "
                f"expected {expected_size}, got {actual_size}"
            )
            continue
        
        # Check hash if present
        if "sha256" in file_info:
            actual_hash = _compute_file_hash(file_path)
            if actual_hash != file_info["sha256"]:
                errors.append(
                    f"Hash mismatch for {file_info['path']}: "
                    f"expected {file_info['sha256']}, got {actual_hash}"
                )
                continue
        
        verified_files.append(file_info["path"])
    
    # Check for extra files not in manifest
    manifest_files = {f["path"] for f in manifest.get("files", [])}
    for file_path in run_dir.rglob("*"):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(run_dir))
            if rel_path not in manifest_files and rel_path != "manifest.json":
                warnings.append(f"Extra file not in manifest: {rel_path}")
    
    return {
        "verified": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "verified_files": len(verified_files),
        "total_files": len(manifest.get("files", [])),
        "manifest_hash": manifest.get("manifest_hash", ""),
    }


def _compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """Compute hash of a file."""
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def save_manifest(
    manifest: Dict[str, Any],
    output_path: Union[str, Path],
):
    """
    Save manifest to file.
    
    Args:
        manifest: Manifest dictionary
        output_path: Output file path
    """
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)


def compare_manifests(
    manifest1: Dict[str, Any],
    manifest2: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare two manifests for differences.
    
    Args:
        manifest1: First manifest
        manifest2: Second manifest
        
    Returns:
        Dictionary with comparison results
    """
    differences = []
    
    # Compare configs
    config1 = manifest1.get("config", {})
    config2 = manifest2.get("config", {})
    
    config_keys = set(config1.keys()) | set(config2.keys())
    for key in config_keys:
        val1 = config1.get(key)
        val2 = config2.get(key)
        if val1 != val2:
            differences.append({
                "type": "config",
                "key": key,
                "value1": val1,
                "value2": val2,
            })
    
    # Compare system snapshots
    sys1 = manifest1.get("system_snapshot", {})
    sys2 = manifest2.get("system_snapshot", {})
    
    important_sys_keys = ["device_model", "os_version", "python_version", "cpu_governor"]
    for key in important_sys_keys:
        val1 = sys1.get(key)
        val2 = sys2.get(key)
        if val1 != val2:
            differences.append({
                "type": "system",
                "key": key,
                "value1": val1,
                "value2": val2,
            })
    
    # Compare file counts
    files1 = len(manifest1.get("files", []))
    files2 = len(manifest2.get("files", []))
    
    return {
        "identical": len(differences) == 0,
        "differences": differences,
        "file_count_1": files1,
        "file_count_2": files2,
    }

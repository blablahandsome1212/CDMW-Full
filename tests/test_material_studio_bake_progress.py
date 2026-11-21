"""A texture bake reports its steps to the Mesh Editor while it runs."""

import json

from cdmw.services.host_progress import BAKE_STAGES, HOST_PROGRESS_FILE, host_progress, report_bake_progress


def test_bake_steps_are_written_for_the_editor_and_removed_at_the_end(tmp_path):
    path = tmp_path / HOST_PROGRESS_FILE
    report_bake_progress(0, 1, "Material 1/1: a. Reading source textures...")
    assert not path.exists()  # No command is reporting.
    with host_progress(tmp_path):
        report_bake_progress(1, 2, "Material 2/2: veil. Compressing colour texture...")
        payload = json.loads(path.read_text())
        assert payload["kind"] == "bake" and (payload["material"], payload["materials"]) == (2, 2)
        assert payload["stage"] == BAKE_STAGES.index("Compressing colour texture...")
        assert payload["fraction"] == (6 + 3) / 12
        # A cached bake finishes its material at once; other log lines change nothing.
        report_bake_progress(0, 2, "Material 1/2: veil. Reusing prepared textures.")
        assert json.loads(path.read_text())["fraction"] == 0.5
        report_bake_progress(0, 2, "Material 1/2: veil. Leaving out a height texture that is not available: x")
        assert json.loads(path.read_text())["fraction"] == 0.5
    assert not path.exists()

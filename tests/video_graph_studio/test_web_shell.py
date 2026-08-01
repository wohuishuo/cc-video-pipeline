from pathlib import Path


WEB = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio" / "web"


def test_shell_has_creator_controls_and_workflow_regions():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert 'for="source-root"' in html
    assert 'for="voice"' in html
    assert 'aria-label="Target languages"' in html
    assert 'aria-label="Target platforms"' in html
    assert 'id="capability-palette"' in html
    assert 'id="workflow-canvas"' in html
    assert 'id="node-inspector"' in html
    assert 'id="activity-log"' in html
    assert 'aria-label="Workflow template"' in html
    assert 'value="prepared-localization"' in html
    assert 'value="folder-intake"' in html
    assert 'value="url-intake"' in html
    assert 'id="source-url"' in html
    assert "onclick=" not in html.lower()


def test_shell_loads_only_local_versioned_assets():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'href="/styles.css?v=1"' in html
    assert 'src="/app.js?v=1"' in html
    assert "https://" not in html
    assert "http://" not in html


def test_client_uses_versioned_run_contracts_and_stops_terminal_polling():
    script = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'contractId: "CMD-RUN-CREATE"' in script
    assert 'contractId: "CMD-RUN-START"' in script
    assert 'contractVersion: "1.0"' in script
    assert "crypto.randomUUID()" in script
    assert 'TERMINAL_STATES.has(run.status)' in script
    assert "templateId" in script
    assert 'sourceUrl' in script
    assert 'folder-intake' in script
    assert 'url-intake' in script
    assert 'sourceRoot.required = !urlMode' in script
    assert 'sourceUrl.required = urlMode' in script
    assert 'node.dataset.stepId' in script
    assert 'dataset.stepId = stepIds[index]' in script
    assert 'TEMPLATE_NODE_COPY' in script
    assert 'const copy = TEMPLATE_NODE_COPY[state.templateId][nodeId]' in script
    assert 'input.disabled = busy' in script
    assert 'function resetRunProjection()' in script
    assert 'state.currentRun = null' in script

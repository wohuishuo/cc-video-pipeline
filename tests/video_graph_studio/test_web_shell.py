from pathlib import Path


WEB = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio" / "web"


def test_shell_is_a_truthful_guided_graph_builder():
    html = (WEB / "index.html").read_text(encoding="utf-8")

    assert 'id="graph-builder"' in html
    assert 'for="workflow-goal"' in html
    assert 'id="workflow-goal"' in html
    assert 'aria-label="Source kind"' in html
    assert 'id="workflow-summary"' in html
    assert 'id="readiness-list"' in html
    assert 'id="reconnect-button"' in html
    assert 'id="graph-track"' in html
    assert 'id="graph-empty-state"' in html
    assert 'id="zoom-level"' in html
    assert 'id="zoom-out"' in html
    assert 'id="zoom-in"' in html
    assert 'id="fit-graph"' in html
    assert 'Create &amp; run Graph' in html
    assert 'id="capability-palette"' not in html
    assert 'name="template"' not in html
    assert 'aria-label="Select tool"' not in html
    assert 'class="port ' not in html


def test_shell_has_creator_controls_and_workflow_regions():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert 'for="source-root"' in html
    assert 'for="voice"' in html
    assert 'aria-label="Target languages"' in html
    assert 'aria-label="Target platforms"' in html
    assert 'id="graph-builder"' in html
    assert 'id="workflow-canvas"' in html
    assert 'id="node-inspector"' in html
    assert 'id="activity-log"' in html
    assert 'aria-label="Build a Graph"' in html
    assert 'id="publication-credential-id"' in html
    assert 'id="publication-plan-run-id"' in html
    assert 'id="publication-confirmation"' in html
    assert 'id="credential-vault-path"' in html
    assert 'id="publication-batch-execution-controls"' in html
    assert 'id="release-plan-run-id"' in html
    assert 'id="release-execution-confirmation"' in html
    assert 'id="release-credential-vault-path"' in html
    assert 'id="youtube-client-config"' in html
    assert 'id="youtube-vault-path"' in html
    assert 'id="youtube-credential-id"' in html
    assert 'id="creator-max-items"' in html
    assert 'id="authentication-file"' in html
    assert 'id="publication-video"' in html
    assert 'id="publication-metadata"' in html
    assert 'id="release-controls"' in html
    assert 'id="release-metadata-template"' in html
    assert 'id="release-account"' in html
    assert 'id="release-credential-id"' in html
    assert 'aria-label="Release targets"' in html
    assert 'aria-label="Publication targets"' in html
    assert 'id="source-url"' in html
    assert 'id="source-language"' in html
    assert 'id="asr-model"' in html
    assert 'id="asr-device"' in html
    assert 'id="translation-device"' in html
    assert 'id="translation-batch-size"' in html
    assert 'id="inspector-loop"' in html
    assert 'id="inspector-owner"' in html
    assert 'id="inspector-relationship"' in html
    assert 'id="inspector-retry"' in html
    assert 'id="inspector-output"' in html
    assert 'id="access-button"' in html
    assert 'id="access-dialog"' in html
    assert 'id="access-workspace"' in html
    assert 'id="access-token"' in html
    assert "onclick=" not in html.lower()


def test_shell_loads_only_local_versioned_assets():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'href="/styles.css?v=5"' in html
    assert 'type="module" src="/app.js?v=9"' in html
    assert 'src="https://' not in html
    assert 'href="https://' not in html
    assert 'src="http://' not in html
    assert 'href="http://' not in html


def test_client_uses_versioned_run_contracts_and_stops_terminal_polling():
    script = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'contractId: "CMD-RUN-CREATE"' in script
    assert 'contractId: "CMD-RUN-START"' in script
    assert 'api("/api/v1/contracts")' in script
    assert "state.contracts.contractVersion" in script
    assert "async function loadContracts()" in script
    assert "Contract unavailable" in script
    assert "crypto.randomUUID()" in script
    assert 'TERMINAL_STATES.has(run.status)' in script
    assert "function buildPayload(values)" in script
    assert 'sourceUrl' in script and 'sourceRoot' in script
    assert 'metadataTemplatePath' in script and 'targetAccounts' in script
    assert 'checkedValues("release-target")' in script
    assert 'sourceVolume' in script
    assert 'creator-profile' in script and 'creator-batch-dub' in script
    assert 'maxItems' in script and 'authenticationFile' in script
    assert 'publication-plan' in script and 'publication-execute' in script
    assert 'publication-batch-execute' in script and 'youtube-connect' in script
    assert 'planRunId' in script and 'confirmation' in script and 'credentialVaultPath' in script
    assert 'clientConfigPath' in script and 'credentialId' in script and 'label' in script
    assert 'credentialIds' in script
    assert 'function populateLatestPublicationPlan()' in script
    assert 'function populateLatestPublicationBatchPlan()' in script
    assert 'releasePlanRunId' in script and 'fact.manifestSha256' in script
    assert 'videoPath' in script and 'metadataPath' in script and 'targetPlatforms' in script
    assert 'targetVoices' in script and 'sourceLanguage' in script
    assert 'asrModel' in script and 'asrDevice' in script
    assert 'targetLanguages' in script and 'translationDevice' in script
    assert 'translationBatchSize' in script
    assert 'CONFIG_BY_REQUIREMENT' in script
    assert 'state.currentRun = null' in script
    assert 'sessionStorage.getItem("videoGraph.accessToken")' in script
    assert 'sessionStorage.setItem("videoGraph.accessToken", token)' in script
    assert 'history.replaceState(null, "", `${location.pathname}${location.search}`)' in script
    assert 'Authorization: `Bearer ${token}`' in script
    assert '"X-Workspace-Id": workspaceId' in script

    styles = (WEB / "styles.css").read_text(encoding="utf-8")
    assert ".studio-shell {" in styles
    assert "grid-template-columns: 340px minmax(0,1fr) 300px" in styles
    assert ".graph-track { --graph-zoom:1" in styles
    assert ".graph-node {" in styles


def test_client_composes_catalog_readiness_and_exact_dynamic_graph():
    script = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'from "./workflow-model.mjs"' in script
    assert 'api("/api/v1/capabilities")' in script
    assert "async function reconnect()" in script
    assert "function renderReadiness()" in script
    assert "function renderGraph()" in script
    assert "function handleGraphNodeClick" in script
    assert '$("#graph-track").addEventListener("click", handleGraphNodeClick)' in script
    assert "groupWorkflowGoals" in script
    assert "resolveTemplate" in script
    assert "evaluateReadiness" in script
    assert "projectGraph" in script
    assert "nextZoom" in script
    assert "TEMPLATE_NODE_COPY" not in script
    assert 'input[name="template"]' not in script
    assert "data-focus-node" not in script

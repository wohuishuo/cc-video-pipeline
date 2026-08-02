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
    assert 'value="folder-transcription"' in html
    assert 'value="url-transcription"' in html
    assert 'value="folder-translation"' in html
    assert 'value="url-translation"' in html
    assert 'value="folder-voice"' in html
    assert 'value="url-voice"' in html
    assert 'value="folder-dub"' in html
    assert 'value="url-dub"' in html
    assert 'value="folder-release"' in html
    assert 'value="url-release"' in html
    assert 'value="creator-profile"' in html
    assert 'value="creator-batch-dub"' in html
    assert 'value="publication-plan"' in html
    assert 'value="publication-execute"' in html
    assert 'value="youtube-connect"' in html
    assert 'id="publication-credential-id"' in html
    assert 'id="publication-plan-run-id"' in html
    assert 'id="publication-confirmation"' in html
    assert 'id="credential-vault-path"' in html
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
    assert 'id="output-format"' in html
    assert 'id="output-evidence"' in html
    assert 'id="access-button"' in html
    assert 'id="access-dialog"' in html
    assert 'id="access-workspace"' in html
    assert 'id="access-token"' in html
    assert "onclick=" not in html.lower()


def test_shell_loads_only_local_versioned_assets():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'href="/styles.css?v=3"' in html
    assert 'src="/app.js?v=7"' in html
    assert "https://" not in html
    assert "http://" not in html


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
    assert "templateId" in script
    assert 'sourceUrl' in script
    assert 'folder-intake' in script
    assert 'url-intake' in script
    assert 'folder-transcription' in script
    assert 'url-transcription' in script
    assert 'folder-translation' in script
    assert 'url-translation' in script
    assert 'folder-voice' in script
    assert 'url-voice' in script
    assert 'folder-dub' in script
    assert 'url-dub' in script
    assert 'folder-release' in script
    assert 'url-release' in script
    assert 'releaseMode' in script
    assert 'metadataTemplatePath' in script
    assert 'targetAccounts' in script
    assert 'input[name="release-target"]:checked' in script
    assert 'state.templateId.endsWith("-release") ? "0 / 12"' in script
    assert 'sourceVolume' in script
    assert 'creator-profile' in script
    assert 'creator-batch-dub' in script
    assert 'creatorBatchMode' in script
    assert 'maxItems' in script
    assert 'authenticationFile' in script
    assert 'publication-plan' in script
    assert 'publication-execute' in script
    assert 'youtube-connect' in script
    assert 'planRunId' in script and 'confirmation' in script and 'credentialVaultPath' in script
    assert 'clientConfigPath' in script and 'credentialId' in script and 'label' in script
    assert 'credentialIds' in script
    assert 'function populateLatestPublicationPlan()' in script
    assert 'fact.manifestSha256' in script
    assert 'videoPath' in script and 'metadataPath' in script and 'targetPlatforms' in script
    assert 'targetVoices' in script
    assert 'sourceLanguage' in script
    assert 'asrModel' in script
    assert 'asrDevice' in script
    assert 'targetLanguages' in script
    assert 'translationDevice' in script
    assert 'translationBatchSize' in script
    assert '"JSON · SRT"' in script
    assert '"Source Manifest"' in script
    styles = (WEB / "styles.css").read_text(encoding="utf-8")
    assert ".template-field{flex:1 0 100%}" in styles
    assert ".runbar { height: 126px;" in styles
    assert ".runbar.creator-batch-mode { height: 180px;" in styles
    assert ".runbar.release-mode { height: 220px;" in styles
    assert '$("#run-form").classList.toggle("creator-batch-mode", creatorBatchMode)' in script
    assert '$("#run-form").classList.toggle("release-mode", releaseMode)' in script
    assert '$("#release-controls").hidden = !releaseMode' in script
    assert 'sourceRoot.required = !urlMode' in script
    assert 'sourceUrl.required = urlMode' in script
    assert 'node.dataset.stepId' in script
    assert 'dataset.stepId = stepIds[index]' in script
    assert 'TEMPLATE_NODE_COPY' in script
    assert 'const copy = TEMPLATE_NODE_COPY[state.templateId][nodeId]' in script
    assert 'input.disabled = busy' in script
    assert 'function resetRunProjection()' in script
    assert 'state.currentRun = null' in script
    assert 'sessionStorage.getItem("videoGraph.accessToken")' in script
    assert 'sessionStorage.setItem("videoGraph.accessToken", token)' in script
    assert 'history.replaceState(null, "", `${location.pathname}${location.search}`)' in script
    assert 'Authorization: `Bearer ${token}`' in script
    assert '"X-Workspace-Id": workspaceId' in script

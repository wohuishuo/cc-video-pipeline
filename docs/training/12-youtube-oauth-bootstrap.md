# Tutorial: connect a YouTube account

## 1. Create the desktop client

In Google Cloud Console, enable YouTube Data API v3, configure the consent screen and create an OAuth client of type **Desktop app**. Download its JSON file. Google does not allow OAuth clients to be created automatically.

## 2. Open Video Graph Studio

Choose **Connect YouTube**. Enter the downloaded client JSON path, a Credential Vault JSON path inside your Windows user profile, a reusable ID such as `youtube-main`, and a label.

## 3. Run the Graph

Studio queues two nodes. OAuth Bootstrap opens the system browser and requests only YouTube upload permission. After consent, the browser returns to an ephemeral `127.0.0.1` callback. The second node asks Credential Vault to confirm that the resulting credential is active and provider-bound to YouTube.

If the system browser does not open, copy the authorization URL from the activity log into a full browser. Do not use an embedded webview.

## 4. Publish privately

Use the same credential ID in **Publish Plan**, then provide the plan SHA and Vault path in **Publish Execute**. The publisher always requests private visibility and requires a returned video ID plus explicit private status.

Current automated evidence stops before real Google consent. The first real connection and upload remain deliberate account-owner actions.

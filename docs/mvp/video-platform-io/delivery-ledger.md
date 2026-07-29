# Delivery ledger

| Capability | Stage | Evidence / blocker |
|---|---|---|
| Portable launcher and installers | domain-verified | `$PSScriptRoot` paths, pinned Git revisions, tests |
| YouTube download | production-verified | real 1080p file + FFprobe receipt |
| Bilibili download | production-verified | real 720p file + FFprobe receipt; 1080 not proven |
| Douyin download | implemented | both adapters invoked; current public URL requires working cookie/session |
| TikTok download | implemented | both adapters invoked; current extraction/token generation blocked upstream |
| YouTube/Bilibili/Douyin upload | implemented | pinned uploader launches and commands prepare; account draft not tested |
| TikTok upload | implemented | isolated browser bridge and prepared command; account draft not tested |

No upload capability is labeled platform-integrated or production-verified until an account owner logs in and deliberately runs an upload to draft/private state.

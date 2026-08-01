# One-video-at-a-time Russian localization

Process the existing 74-video manifest sequentially. Each video gets its own Qwen process, then is mixed and rendered into `russian/final` before the next video starts. Completed clips and completed final videos remain reusable after restart.

Only one Qwen worker may exist at once. A failed video is recorded and the batch continues. Exiting the worker between videos releases CUDA memory and prevents cumulative GPU growth across the whole creator archive.


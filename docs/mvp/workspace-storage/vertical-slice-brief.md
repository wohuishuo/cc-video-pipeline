# Workspace Storage vertical slice brief

Observable result: an operator provisions two workspace IDs below one canonical storage root, receives disjoint state/artifact/temp namespaces, safely resolves relative paths and gets an inspectable capacity decision.

Workspace Storage owns namespace binding, path confinement and current-byte capacity projection. Workspace Access owns identity and admission. Graph Studio owns runs. Media MVPs own the meaning and validity of files written below artifact roots.

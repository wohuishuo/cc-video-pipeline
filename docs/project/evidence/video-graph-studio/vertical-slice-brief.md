# Video Graph Studio Vertical Slice Brief

| Field | Content |
| --- | --- |
| Observable result | A creator uses a local browser to create, start and observe strictly serial intake, transcription or multilingual translation graphs with durable step state and logs. |
| Use cases | list capabilities; browse allowed folders; accept supported video URL; choose ASR and translation policies; create/replay run; start/resume run; cancel run; query run and logs |
| State owners | Graph Definition, Workflow Run, Workflow Process, Local Worker Runtime, Run Log and Dashboard Projection are separate owners. |
| Protected invariants | stable operation identity; conflicting replay rejection; optimistic versions; one active process; checkpoint recovery; read-only projection; loopback/path security |
| Decision gates | hosted identity, billing, remote authentication, paid translation fallback and unattended platform publication remain unapproved |
| Non-goals | voice rendering from the new Translation Manifest, subtitle/video composition, creator-profile enumeration, arbitrary user code nodes, parallelism, cloud hosting and production-verified social upload |

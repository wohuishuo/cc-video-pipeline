# Video Graph Studio Vertical Slice Brief

| Field | Content |
| --- | --- |
| Observable result | A creator uses a local browser to create, start and observe a strictly serial prepared-folder localization graph with durable step state and logs. |
| Use cases | list capabilities; browse allowed folders; create/replay run; start/resume run; cancel run; query run and logs |
| State owners | Graph Definition, Workflow Run, Workflow Process, Local Worker Runtime, Run Log and Dashboard Projection are separate owners. |
| Protected invariants | stable operation identity; conflicting replay rejection; optimistic versions; one active process; checkpoint recovery; read-only projection; loopback/path security |
| Decision gates | hosted identity, billing, remote authentication, paid translation fallback and unattended platform publication remain unapproved |
| Non-goals | raw-folder transcription, arbitrary user code nodes, parallelism, cloud hosting and production-verified social upload |


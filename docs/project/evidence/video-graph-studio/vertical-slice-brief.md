# Video Graph Studio Vertical Slice Brief

| Field | Content |
| --- | --- |
| Observable result | A creator uses a local browser to create, queue, observe, cancel and recover serial acquisition/localization/publication-planning Graphs, optionally under workspace admission, isolated roots and resource leases. |
| Use cases | list capabilities; browse allowed folders; accept supported video URL/profile; choose ASR, languages, voices and targets; create/replay; start/resume; cancel; query queue/run/logs |
| State owners | Graph Definition, Workflow Run, Durable Queue, Workflow Process, Local Worker Runtime, Run Log, Dashboard Projection and Resource Budget remain separate owners. |
| Protected invariants | stable operation identity; conflicting replay rejection; optimistic versions; one active process; checkpoint recovery; lease-before-running; no completion after lease loss; read-only projection; loopback/path security |
| Decision gates | hosted identity, billing, remote authentication, paid translation fallback and unattended platform publication remain unapproved |
| Non-goals | arbitrary browser code nodes, parallelism, automatic public upload, cloud hosting, distributed resource enforcement and production-verified social upload |

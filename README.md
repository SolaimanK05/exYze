# exYze

exYze turns a floor plan into a 3D building you can walk through, edit and share. A plan can come in as a DXF file from CAD software or as a phone photo of a printed plan. The system detects walls, doors, windows, rooms and furniture, stores them as a versioned building model in PostgreSQL, and gives an estimate of the building cost.

Term project for CSE 4510 (Software Development Lab) and CSE 4508 (RDBMS Programming Lab), IUT.

## Tech stack

| Part | Tools |
| --- | --- |
| Frontend | React, TypeScript, Three.js (React Three Fiber), Konva |
| Backend | Python, FastAPI |
| Plan import | ezdxf (DXF), OpenCV, CubiCasa5K, PaddleOCR (photos) |
| Database | PostgreSQL with PostGIS |
| Tooling | Docker, GitHub Actions |

## Repository layout

| Folder | Contents |
| --- | --- |
| `frontend/` | Web app: 2D editor, 3D viewer, sharing |
| `backend/` | API and the import worker |
| `db/` | Schema, functions, procedures, triggers and seed data |
| `ml/` | Floor plan model and dimension reading for photos |
| `docs/` | Design notes and diagrams |

## Team

| Member | Role |
| --- | --- |
| Mahmudul Hassan Turjo | Geometry engine |
| S. M. Solaiman Kalam | Detection and furniture |
| Rakin Al Shahriar | 3D viewer and editing |
| Abdullah Ibn Yousuf | Database core and API |
| Samman Rahin Shanto | Photo capture and platform |
| Md. Jahidul Islam | 2D editor and sharing, Scrum master |

## How we work

`main` is protected. Nobody pushes to it directly.

1. Pull the latest `main` and create a branch for your task, for example `feature/wall-detection`.
2. Commit your work to that branch using your own GitHub account.
3. Push the branch and open a pull request into `main`.
4. Another teammate reviews and approves it, then it is squash-merged.

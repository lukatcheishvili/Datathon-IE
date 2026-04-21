# Zero Heroes: Strategic EV Infrastructure Optimization
## IE-Iberdrola Datathon 2026

### Executive Summary
The Zero Heroes project provides a data-driven framework for the strategic expansion of electric vehicle (EV) charging infrastructure across Spain's interurban highway network. By integrating 2027 EV growth projections with real-world distribution grid capacity data, the solution identifies optimal locations for new infrastructure while proactively mapping logistical "Friction Points" where grid congestion may impact deployment timelines.

---

### Core Analytical Methodology

The analytical engine utilizes a dual-strategy approach to infrastructure placement, ensuring both coverage and capacity scalability:

#### 1. EXPAND Strategy (Capacity Scaling)
This strategy identifies existing charging stations currently experiencing high utilization pressure. By applying a 2027 EV growth multiplier to current registration data, the engine identifies the top 30% of stations requiring immediate hardware expansion to prevent future bottlenecks.

#### 2. FILL Strategy (Coverage Gap Analysis)
The engine performs a spatial "Blind Spot" analysis across the interurban network (Highways AP, A, E, and N). It identifies segments where no charging infrastructure exists within a 100km radius. Candidate points are then generated using a weighted distribution based on the road's strategic importance (MITMA traffic flows).

#### 3. Grid Capacity Integration
Every proposed location is spatially cross-referenced with substation data from Spain's three primary distributors (i-DE, Endesa, and Viesgo). Each site is assigned a "Grid Status" (Sufficient, Moderate, or Congested) based on the available firmware capacity (MW) of the nearest substation.

---

### Cloud Infrastructure and Data Pipeline

To ensure the portability and scalability of the analysis, a hybrid cloud architecture was implemented to synchronize code, large-scale datasets, and the execution environment:

#### 1. GitHub Integration
The GitHub repository serves as the primary orchestration hub, managing all source code, business logic, and small-to-medium datasets. The repository is integrated directly into the Google Colab environment via a programmatic Git-Sync engine.

#### 2. Google Cloud Storage (GCS) Backbone
Large-scale datasets (such as high-resolution road geometry shapefiles and multi-million row MITMA matrices) are hosted on a dedicated **Google Cloud Storage Public Bucket**. This architecture bypasses GitHub’s storage limitations and ensures high-speed data throughput during notebook execution.

#### 3. Automated Provisioning Pipeline
A custom infrastructure-as-code script (`setup_infrastructure.ps1`) was utilized to automate the deployment. This script:
- Provisions a unique GCP project and storage bucket.
- Configures IAM permissions for public read access.
- Executes multi-threaded data uploads via `gsutil` to ensure data integrity and speed.

---

### Technical Implementation

The solution is implemented as a single-file Master Orchestrator (`working.ipynb`) designed for seamless execution in cloud environments.

#### High-Performance Data Processing
- **Polars Engine**: Utilized for sub-second processing of massive datasets, including over 1 million MITMA road trip records and DGT vehicle registration files.
- **Spatial Intelligence**: GeoPandas and PyProj are used for coordinate transformation (UTM to EPSG:4326) and nearest-neighbor spatial joins between proposed sites and electrical substations.
- **Cloud-Native Design**: The notebook includes an autonomous synchronization layer that handles dependency management and repository cloning automatically upon initialization in Google Colab.

---

### Data Sources and Integrity
- **DGT (Dirección General de Tráfico)**: Historical registration data used for EV growth modeling (Filtering for Propulsion Code '2').
- **MITMA (Ministerio de Transportes)**: Road flow and trip matrix data used for interurban segment weighting.
- **Distribution Network Data**: Unified substation capacity maps from i-DE, Endesa, and Viesgo e-distribución.
- **Natural Earth**: Global administrative and road network geometry for spatial clipping.

---

### Submission Deliverables

The pipeline generates three standardized output files as per the Datathon specifications:

1.  **File_1.csv (KPI Scorecard)**: A high-level summary containing global metrics including total proposed stations, existing baseline infrastructure, and total friction points identified.
2.  **File_2.csv (Proposed Locations)**: A comprehensive list of proposed sites featuring latitude/longitude, route segments, proposed charger counts, and strategic pressure scores.
3.  **File_3.csv (Friction Points)**: A focused list of locations with 'Moderate' or 'Congested' grid status, mapped to their respective distributor network (i-DE, Endesa, or Viesgo).

---

### Instructions for Replication

To replicate the analysis or review the results:

1.  Upload the **`working.ipynb`** file to a Google Colab environment.
2.  Execute the **Environment Setup and Data Synchronization** cell. This cell will automatically clone the repository and install all required analytical libraries.
3.  Select **Runtime > Run All**. 
4.  The output CSV files will be generated in the root directory of the Colab environment.

---

### Project Context and Team
This project was developed for the IE-Iberdrola Datathon 2026.

**Project Members**: Luka Tcheishvili, Andrea Alarcón, Diego Gaitán, Sacha Huberty, Dalton Kern, Romain Gelin 
**Institution**: IE University
**Date**: April 2026

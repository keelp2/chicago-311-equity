# Chicago 311: Do Wealthier Neighborhoods Get Faster City Services?

An equity analysis of Chicago's 311 service request system, investigating whether response times and service quality vary by neighborhood income level.

**[View the Analysis Notebook](notebooks/analysis.ipynb)**

## Question

Chicago receives millions of 311 service requests each year — potholes, streetlights, rodent complaints, graffiti, and more. **Do all neighborhoods receive the same quality of service, or do wealthier areas get faster responses?**

## Approach

1. **Data Collection** — 14.7M service requests from the [Chicago Data Portal](https://data.cityofchicago.org/Service-Requests/311-Service-Requests/v6vf-nfxy) via the Socrata API
2. **Income Enrichment** — Join with Census ACS median household income by community area
3. **Response Time Analysis** — Statistical comparison of resolution times across income quartiles
4. **NLP on Complaint Text** — Topic modeling to understand what different neighborhoods report
5. **Geospatial Visualization** — Map response time disparities across the city
6. **Statistical Testing** — Hypothesis tests to determine if observed differences are significant

## Key Findings

*(To be completed)*

## Data Sources

| Source | Description |
|--------|-------------|
| [Chicago 311 Service Requests](https://data.cityofchicago.org/Service-Requests/311-Service-Requests/v6vf-nfxy) | 14.7M requests with timestamps, locations, status, ward, community area |
| [Census ACS](https://data.census.gov/) | Median household income by community area |
| [Chicago Community Areas](https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas-current-/cauq-8yn6) | GeoJSON boundaries for mapping |

## Repo Structure

```
notebooks/
  analysis.ipynb       ← main analysis (start here)
scripts/
  pull_data.py         ← download 311 data from Socrata API
data/                  ← local data files (gitignored)
figures/               ← saved plots for README
requirements.txt       ← Python dependencies
```

## Run Locally

```bash
pip install -r requirements.txt
python scripts/pull_data.py
jupyter notebook notebooks/analysis.ipynb
```

## Tools

Python, Pandas, Scikit-learn, Plotly, Folium, SciPy, Socrata API

---

Built by [Peter Keel](https://keelp2.github.io)

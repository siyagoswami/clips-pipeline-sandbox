from pathlib import Path 
from google.cloud import bigquery 

OUTPUT_PATH = Path("input/dim_jurisdictions.csv")
TABLE_NAME = "`early-warning-system-prod.jurisdictions.dim_jurisdictions`"

def main() -> None:
    client = bigquery.Client()

    query = f"""
        SELECT
            jurisdiction_id,
            jurisdiction_type,
            jurisdiction_name,
            normalized_name,
            census_geoid,
            state_fips,
            state_abbr,
            county_name,
            county_geoid
        FROM {TABLE_NAME}
        WHERE jurisdiction_id IS NOT NULL
          AND normalized_name IS NOT NULL
    """

    print("Running query...")
    dataframe = client.query(query).to_dataframe()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(OUTPUT_PATH, index=False)

    print(f"Exported {len(dataframe)} jurisdictions to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
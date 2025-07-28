# Domain.com.au Property Scraper (v6)

This project contains a powerful and stable Python script (`v6_reverted.py`) for scraping residential rental property data from Domain.com.au. It is designed to be robust, configurable, and easy to use.

## Key Features

- **Stable & Robust**: Built upon a proven, stable codebase to ensure reliable scraping.
- **Rich Data Extraction**: Captures a wide range of data points, including property details, pricing, agent information, and a comprehensive list of features.
- **Dynamic Feature Management**: The standout feature of this version. You can define which property features to scrape (e.g., "Balcony", "Dishwasher", "Pet Friendly") by simply editing a configuration file, without touching any Python code.
- **Excel Output**: Generates a clean, timestamped `.xlsx` file for each scraped URL, ready for analysis.
- **Configurable**: Scraper behavior (network settings, delays) can be fine-tuned via `config/crawler_config.yaml`.

## Setup

Ensure you have Python 3.x and pip installed.

To install all necessary Python libraries, run:
```bash
pip install pandas requests lxml PyYAML openpyxl
```

## How to Run

1.  **Configure URLs**: Edit the `config/url.txt` file. Add one or more Domain.com.au search result URLs, one per line. For a quick test, you can use `config/temp_urls.txt` which, if it contains any URLs, will be used instead of `url.txt`.

2.  **Run the Script**: Execute the main script from your terminal:
    ```bash
    python v6_reverted.py
    ```

3.  **Find Your Data**: The script will process each URL and save the results as a separate `.xlsx` file in the `output/` directory. The filename will be timestamped and include the region name (e.g., `20250728_212216_Forest_Lodge_14properties.xlsx`).

## Dynamic Feature Management

This script's most powerful feature is its ability to be customized without editing code. You can control exactly which property features are detected and added as columns to the final Excel file.

This is all managed in the **`config/features_config.yaml`** file.

### How it Works

The script reads the `features_config.yaml` file at startup. For each feature defined in the file, it will:
1.  Dynamically add a corresponding boolean (TRUE/FALSE) column to the output Excel file.
2.  Scan the property's description and feature list for the keywords you've specified.
3.  If any keyword is found, the value in the corresponding column for that property will be set to `TRUE`.

### `features_config.yaml` Structure

The file is a list of features. Each feature has three parts:

-   `name`: The Chinese name for the feature (for reference).
-   `column_name`: The name of the column in the output Excel file. **Must be a valid Python variable name** (e.g., `has_dishwasher`, no spaces).
-   `keywords`: A list of keywords to search for in the property description. The search is case-insensitive.

### Example: Adding a "Pet Friendly" Feature

To add a feature that checks if pets are allowed, you would add the following to `config/features_config.yaml`:

```yaml
- name: 允许宠物
  column_name: allows_pets
  keywords:
    - "pet friendly"
    - "pets allowed"
    - "pets considered"
    - "允许宠物"
```

After adding this and re-running the script, your output Excel file will now contain a new column named `allows_pets`, which will be `TRUE` for any property whose description contains one of the specified keywords.

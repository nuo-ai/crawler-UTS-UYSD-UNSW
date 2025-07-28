import pandas as pd
import numpy as np

def style_diff(val):
    """
    Styles the HTML output for differences.
    Colors differing cells red.
    """
    if val is None:
        return ''
    return 'background-color: #ffdddd' if val else ''

def detailed_compare(df1, df2, key_column='listing_id'):
    """
    Performs a detailed comparison between two DataFrames based on a key column.
    """
    # Ensure key column exists
    if key_column not in df1.columns or key_column not in df2.columns:
        raise ValueError(f"Key column '{key_column}' not found in one or both files.")

    # Set index and ensure it's unique
    df1 = df1.set_index(key_column, drop=False)
    df2 = df2.set_index(key_column, drop=False)
    
    if df1.index.duplicated().any():
        print(f"Warning: Duplicate '{key_column}' values found in File 1. Keeping first occurrence.")
        df1 = df1[~df1.index.duplicated(keep='first')]
    if df2.index.duplicated().any():
        print(f"Warning: Duplicate '{key_column}' values found in File 2. Keeping first occurrence.")
        df2 = df2[~df2.index.duplicated(keep='first')]

    # Find common and unique keys
    common_keys = df1.index.intersection(df2.index)
    unique_to_f1 = df1.index.difference(df2.index)
    unique_to_f2 = df2.index.difference(df1.index)

    # Align columns for comparison, handling potentially different column sets
    common_cols = df1.columns.intersection(df2.columns).tolist()
    df1_aligned = df1.loc[common_keys, common_cols].copy()
    df2_aligned = df2.loc[common_keys, common_cols].copy()

    # Find differences in common rows
    # Using numpy to compare because pandas.compare is too high-level
    diff_mask = (df1_aligned.fillna('') != df2_aligned.fillna('')).any(axis=1)
    diff_keys = diff_mask[diff_mask].index
    identical_keys = common_keys.difference(diff_keys)

    # --- Generate Text Report ---
    report_lines = []
    report_lines.append("="*50)
    report_lines.append(" Excel File Comparison Report")
    report_lines.append("="*50 + "\n")

    report_lines.append("--- Summary ---")
    report_lines.append(f"File 1 Rows: {len(df1)}")
    report_lines.append(f"File 2 Rows: {len(df2)}")
    report_lines.append(f"Common Listings ({key_column}): {len(common_keys)}")
    report_lines.append(f"  - Identical Rows: {len(identical_keys)}")
    report_lines.append(f"  - Rows with Differences: {len(diff_keys)}")
    report_lines.append(f"Listings unique to File 1: {len(unique_to_f1)}")
    report_lines.append(f"Listings unique to File 2: {len(unique_to_f2)}")
    report_lines.append("\n")

    if unique_to_f1.any():
        report_lines.append(f"--- Listings Only in File 1 ({len(unique_to_f1)}) ---")
        for key in unique_to_f1:
            report_lines.append(f"  - {key}")
        report_lines.append("\n")

    if unique_to_f2.any():
        report_lines.append(f"--- Listings Only in File 2 ({len(unique_to_f2)}) ---")
        for key in unique_to_f2:
            report_lines.append(f"  - {key}")
        report_lines.append("\n")

    if diff_keys.any():
        report_lines.append(f"--- Detailed Differences ({len(diff_keys)} listings) ---")
        for key in diff_keys:
            report_lines.append(f"\n----- {key_column}: {key} -----")
            row1 = df1_aligned.loc[key]
            row2 = df2_aligned.loc[key]

            # Robustness: Handle cases where de-duplication might leave a DataFrame with one row
            if isinstance(row1, pd.DataFrame):
                row1 = row1.iloc[0]
            if isinstance(row2, pd.DataFrame):
                row2 = row2.iloc[0]

            diffs = row1.compare(row2, align_axis=0, result_names=('File 1', 'File 2'))
            if not diffs.empty:
                # Handle case where compare returns a DataFrame (multiple differences)
                if isinstance(diffs, pd.DataFrame):
                    for col_name, row_data in diffs.iterrows():
                        report_lines.append(f"  Column '{col_name}':")
                        report_lines.append(f"    File 1: {row_data['File 1']}")
                        report_lines.append(f"    File 2: {row_data['File 2']}")
                # Handle case where compare might return a Series (which is unexpected but possible)
                elif isinstance(diffs, pd.Series):
                    col_name = diffs.name if diffs.name else "Unknown Column"
                    report_lines.append(f"  Column '{col_name}':")
                    report_lines.append(f"    File 1: {diffs.get('File 1')}")
                    report_lines.append(f"    File 2: {diffs.get('File 2')}")
    
    # --- Generate HTML Report ---
    # Combine all data for one big table
    combined_df = pd.concat([
        df1.loc[unique_to_f1], 
        df2.loc[unique_to_f2],
        df1.loc[diff_keys],
        df2.loc[diff_keys]
    ]).sort_index()
    
    # Create a mask for styling
    style_mask = pd.DataFrame(False, index=combined_df.index, columns=combined_df.columns)
    for key in diff_keys:
        row1 = df1_aligned.loc[key]
        row2 = df2_aligned.loc[key]
        # Mark differing cells
        style_mask.loc[key] = row1.fillna('') != row2.fillna('')

    styled_df = combined_df.style.apply(
        lambda x: np.where(style_mask, 'background-color: #ffdddd', ''), 
        axis=None
    )

    return "\n".join(report_lines), styled_df


def compare_excel_files(file1, file2, text_output, html_output):
    try:
        print(f"Reading {file1}...")
        df1 = pd.read_excel(file1)
        print(f"Reading {file2}...")
        df2 = pd.read_excel(file2)

        print("Starting detailed comparison...")
        report_text, styled_html = detailed_compare(df1, df2)

        with open(text_output, 'w', encoding='utf-8') as f:
            f.write(f"Comparison of:\n- {file1}\n- {file2}\n\n")
            f.write(report_text)
        print(f"Text report saved to {text_output}")

        styled_html.to_html(html_output, escape=False)
        print(f"HTML report saved to {html_output}")

        print("\nComparison complete.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Use relative paths for robustness
    file1 = r"output/20250727_212602_Zetland_161properties.xlsx"
    file2 = r"output/data/0727/20250727_141050_Zetland_161properties.xlsx"
    
    text_output = "comparison_result.txt"
    html_output = "comparison_result.html"
    
    compare_excel_files(file1, file2, text_output, html_output)

import pandas as pd
import os

def load_mtsamples(filepath="data/mtsamples.csv"):
    """
    Load and clean the MTSamples dataset.
    Returns a filtered DataFrame of discharge summaries.
    """
    df = pd.read_csv(filepath)
    
    print(f"✅ Loaded {len(df)} records")
    print(f"📋 Columns: {list(df.columns)}")
    print(f"📂 Specialties: {df['medical_specialty'].nunique()} unique specialties")
    
    # Clean whitespace
    df = df.dropna(subset=['transcription'])
    df['transcription'] = df['transcription'].str.strip()
    df['description'] = df['description'].str.strip()
    df['medical_specialty'] = df['medical_specialty'].str.strip()
    
    # Filter relevant categories for discharge-like notes
    relevant = [
        'Discharge Summary',
        'General Medicine',
        'Internal Medicine',
        'Surgery',
        'Cardiovascular / Pulmonary'
    ]
    
    filtered_df = df[df['medical_specialty'].isin(relevant)].reset_index(drop=True)
    print(f"🔍 Filtered to {len(filtered_df)} relevant records")
    
    return filtered_df


def get_sample_record(df, index=0):
    """Get a single record for testing."""
    record = df.iloc[index]
    return {
        "id": index,
        "specialty": record['medical_specialty'],
        "description": record['description'],
        "transcription": record['transcription']
    }


if __name__ == "__main__":
    df = load_mtsamples()
    sample = get_sample_record(df, index=0)
    print("\n--- Sample Record ---")
    print(f"Specialty: {sample['specialty']}")
    print(f"Description: {sample['description']}")
    print(f"Transcription (first 500 chars):\n{sample['transcription'][:500]}")